# 04 - Groq Migration

Purpose: replace AWS Bedrock with the Groq API behind a thin provider interface, with structured outputs, timeouts, retries, fallback and a cost guard.
Date: 2026-10-26 | Status: design ready, not started | Depends on: Phase 0 of `03-implementation-plan.md`
Unverified items are marked `[?]`. **Model names are intentionally not chosen here**: the current Groq model catalogue and limits must be confirmed from Groq's own documentation in `docs/plan/08-feature-research.md`; code reads names from env vars only.

## 1. Current AI flow (as-built, verified from code)

| Item | Fact |
|---|---|
| Provider | AWS Bedrock Converse via sync `boto3` (`services/bedrock_service.py`). Default model env `BEDROCK_LLM_MODEL=us.meta.llama4-scout-17b-instruct-v1:0`, `BEDROCK_ENABLED`, `BEDROCK_MAX_TOKENS=220`, `BEDROCK_TEMPERATURE=0.2`, AWS keys from env (`config.py:20-27`). |
| Client | Module singleton, no `botocore.Config` (default 60 s timeouts, default retries). |
| Entry points | `chat_completion(system_prompt, messages, max_tokens, temperature, model_id)` and a separate `generate_bedrock_insights(metrics)` (no system prompt). Consumers: intent classifier, data extractor, question generator, orchestrator (confirmation, general chat), session naming (background thread), `/ai/insights`. |
| Message sanitising | Drops leading assistant turns, merges consecutive same-role turns, injects "Hello" if empty (`bedrock_service.py:73-93`). Must be preserved in the provider-neutral layer (Groq does not require alternation, but history hygiene still matters). |
| JSON output | Prompt-only ("respond with ONLY JSON") + markdown-fence stripping + `json.loads` (`intent_classifier.py:70-82`, `data_extractor.py:76-99`). No schema validation, no repair. |
| Failure handling | `BedrockServiceError` -> deterministic text per call site (canned reply, generic question, `GENERAL_CHAT` intent, fallback insights). Good behaviour to keep. |
| Cost / abuse control | None. 3 calls per message, 2000-char input cap only. |
| Concurrency | Sync calls inside async handlers (blocks event loop, audit CA-01/SEC-02); DB connection held during calls (SEC-07). |
| State | Redis session context (`session_manager.py`), last 20 turns, TTL 1 h. |
| Prompt location | `ai_engine/prompts.py` plus strings embedded in `bedrock_service.py:117`, `session_naming.py:19`, `orchestrator.py:247`, `data_extractor.py:50`, `question_generator.py:~50`. Extractor system prompt has literal `{{ }}` (CA-27). |
| Tests | None. |

## 2. Target design

### 2.1 Package layout
```
backend/app/services/llm/
  __init__.py          # exports get_provider(), LLMRequest, LLMResponse, errors
  base.py              # Protocol + dataclasses + exceptions
  factory.py           # chooses provider from settings (groq | bedrock | fake)
  groq_provider.py     # httpx.AsyncClient, OpenAI-compatible chat completions
  bedrock_provider.py  # temporary adapter around current code (rollback path), deleted at cutover
  fake_provider.py     # deterministic, scripted responses for tests/dev/CI
  guard.py             # budget, concurrency, circuit breaker, input caps
  json_utils.py        # strict JSON parse + Pydantic validate + one repair attempt
backend/app/services/ai_engine/
  prompts.py           # ALL prompt text (system, templates, few-shots)
  schemas.py           # Pydantic result models (IntentResult, ContactExtract, DealExtract, ActivityExtract, ...)
  fallbacks.py         # rule-based intent/extraction used when provider unavailable
```
Why httpx and not the vendor SDK `[?]`: Groq exposes an OpenAI-compatible HTTP API (`/openai/v1/chat/completions`) `[?]` - confirm base URL, JSON-mode and rate-limit headers in Groq docs; a ~150-line httpx client keeps the surface small, is trivial to mock (`httpx.MockTransport`), and avoids SDK drift. The official async SDK is an acceptable alternative behind the same interface.

### 2.2 Provider interface (sketch)
```python
# base.py
from dataclasses import dataclass, field
from typing import Literal, Protocol, TypeVar
from pydantic import BaseModel

Role = Literal["system", "user", "assistant"]
T = TypeVar("T", bound=BaseModel)

@dataclass(frozen=True)
class Message:
    role: Role
    content: str

@dataclass(frozen=True)
class LLMRequest:
    messages: list[Message]
    task: str                       # "intent" | "extract" | "question" | "confirm" | "chat" | "title" | "insights" | "draft"
    tier: Literal["fast", "smart"] = "fast"   # maps to env model names
    max_output_tokens: int = 300
    temperature: float = 0.0
    json_mode: bool = False
    user_id: str | None = None      # for budget + logs (never logged with content)

@dataclass(frozen=True)
class LLMUsage:
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    model: str
    provider: str

@dataclass(frozen=True)
class LLMResponse:
    text: str
    usage: LLMUsage

class LLMError(Exception): ...
class LLMTimeout(LLMError): ...
class LLMRateLimited(LLMError):
    retry_after_s: float | None
class LLMBudgetExceeded(LLMError): ...
class LLMBadOutput(LLMError): ...
class LLMUnavailable(LLMError): ...     # circuit open / 5xx after retries

class LLMProvider(Protocol):
    name: str
    async def complete(self, req: LLMRequest) -> LLMResponse: ...

async def complete_json(provider: LLMProvider, req: LLMRequest, schema: type[T]) -> tuple[T, LLMUsage]: ...
```
Call sites pass `task` + `tier` and never a model name; the provider maps `tier` to `GROQ_MODEL_FAST` / `GROQ_MODEL_SMART`.

### 2.3 Structured JSON outputs
1. Request `json_mode=True` (Groq JSON object mode `[?]`; JSON-schema-constrained output exists for some models only `[?]` - decide per model in 08). Always validate on our side regardless.
2. `complete_json` parses, validates with the Pydantic result model (`extra="forbid"`, `Literal` enums, `Decimal`), and on failure performs **one** repair call that includes the validation error text (no user data beyond the failed JSON), then raises `LLMBadOutput`.
3. Call sites catch `LLMError` and use `fallbacks.py` (regex phone/email extraction, keyword intent, canned questions) - the same degrade-don't-crash behaviour as today.
4. Pre-extract with deterministic code before the model: E.164 phone (`+91`/10-digit), email, ISO/relative dates. The model only fills what regex cannot (names, notes, intent). This lowers token use, PII egress and failure rate.
5. Collapse calls: intent + extraction in **one** JSON call (`{"intent":..., "fields":{...}, "missing":[...]}`) with the entity schema in the prompt; question/confirmation texts become templates (EN/TA) with the model only for free chat. Target: 1 call per ordinary turn instead of 3.

### 2.4 Prompts (kept in `prompts.py`)
- All system prompts, user-prompt templates and few-shot examples live in `prompts.py` as constants + small builder functions; call sites contain no prose.
- Untrusted text is always wrapped: `<user_message>...</user_message>`, `<crm_notes>...</crm_notes>`; system prompt states these are data, not instructions; delimiters stripped from the content first.
- Languages: English, Tamil, Tanglish few-shots for intent and extraction (examples are part of the fixture set).
- Prompt version string constant (`PROMPT_VERSION = "2026-10-26.1"`) logged with each call for regression tracking.
- Fix the literal-brace bug (CA-27) while moving.

### 2.5 Timeouts, retries, fallback chain
| Aspect | Setting (env, defaults are proposals) |
|---|---|
| Timeouts | `LLM_CONNECT_TIMEOUT_S=3`, `LLM_READ_TIMEOUT_S=15`, overall per-call deadline `LLM_TOTAL_TIMEOUT_S=20` via `asyncio.timeout`. Whole chat turn budget 25 s. |
| Retries | `LLM_MAX_RETRIES=2` on timeout, connection error, 429, 5xx. Exponential backoff with full jitter (0.4 s base, 3 s cap). On 429 honour `Retry-After` / reset headers `[?]` if <= 5 s, else fail fast to fallback. No retry on 400/401/403/422. |
| Model fallback | `smart` tier failure -> `fast` tier once (if different) -> rule-based fallback. Optional secondary env `GROQ_MODEL_FALLBACK`. |
| Circuit breaker | After `LLM_CIRCUIT_FAILS=5` consecutive failures open for `LLM_CIRCUIT_COOLDOWN_S=30`; half-open single probe. State in-process (single worker) with Redis mirror optional. |
| User-visible degradation | Chat returns the deterministic reply plus `degraded: true` in the response so the UI can show "assistant is in basic mode". |
| Never | Block the event loop; hold a DB connection during the call; retry non-idempotent persistence (only the LLM call is retried). |

### 2.6 Token / cost guard (`guard.py`)
| Control | Behaviour |
|---|---|
| Input cap | `LLM_MAX_INPUT_CHARS=4000` per request after history trimming (keep last N turns that fit); reject user message >2000 chars (existing). |
| Output cap | `max_output_tokens` per task (intent 80, extract 400, question 120, draft 250, title 20, chat 250). Hard ceiling `LLM_MAX_OUTPUT_TOKENS`. |
| Per-user budget | Redis counters `llm:budget:<user>:<yyyymmdd>` with TTL 36 h: `LLM_DAILY_TOKEN_BUDGET_PER_USER=50000` `[?]` tune from real usage, plus `LLM_DAILY_REQUEST_LIMIT_PER_USER=300`. Exceeded -> `LLMBudgetExceeded` -> HTTP 429 `{"detail":"Daily AI limit reached", "degraded": true}` and rule-based fallback for non-chat features. |
| Global budget | `LLM_GLOBAL_DAILY_TOKEN_CAP` kill-switch; ops flag `LLM_ENABLED=false` forces fallback mode. |
| Concurrency | `asyncio.Semaphore(LLM_MAX_CONCURRENCY=8)` shared in-process. |
| Accounting | Add provider-reported `usage` to counters after each call; estimate (chars/4) if usage missing. Log per call: `task, tier, model, prompt_tokens, completion_tokens, latency_ms, outcome, prompt_version, user_hash` - **never** message content or contact fields. |
| Rate-limit headers | Parse remaining-requests/tokens headers `[?]` to slow down proactively when low. |

### 2.7 Environment variables
| Var | Required | Default | Notes |
|---|---|---|---|
| `LLM_PROVIDER` | yes | `groq` (after cutover) | `groq` / `bedrock` (temporary) / `fake` |
| `GROQ_API_KEY` | when groq | none | `SecretStr`; startup fails loudly if provider=groq and empty; never logged |
| `GROQ_BASE_URL` | no | `https://api.groq.com/openai/v1` `[?]` | verify in docs |
| `GROQ_MODEL_FAST` | when groq | none | chosen in 08; no default baked into code |
| `GROQ_MODEL_SMART` | when groq | = FAST | chosen in 08 |
| `GROQ_MODEL_FALLBACK` | no | empty | optional |
| `LLM_ENABLED` | no | `true` | kill switch |
| `LLM_CONNECT_TIMEOUT_S`, `LLM_READ_TIMEOUT_S`, `LLM_TOTAL_TIMEOUT_S` | no | 3 / 15 / 20 | |
| `LLM_MAX_RETRIES` | no | 2 | |
| `LLM_MAX_CONCURRENCY` | no | 8 | |
| `LLM_MAX_INPUT_CHARS`, `LLM_MAX_OUTPUT_TOKENS` | no | 4000 / 600 | |
| `LLM_DAILY_TOKEN_BUDGET_PER_USER`, `LLM_DAILY_REQUEST_LIMIT_PER_USER`, `LLM_GLOBAL_DAILY_TOKEN_CAP` | no | 50000 / 300 / 2000000 | proposals, tune |
| `LLM_CIRCUIT_FAILS`, `LLM_CIRCUIT_COOLDOWN_S` | no | 5 / 30 | |
| Removed at cutover | | | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, `BEDROCK_*` |

Update the single `.env.example`, `docs/docker.md`, `config.py` (use `SecretStr`, validate that provider-specific vars are present), and compose `env_file` for `backend` only.

### 2.8 Orchestrator changes needed for the provider
- `Orchestrator.process_message`, `classify_intent`, `extract_data`, `generate_question`, `generate_session_title` become `async`.
- Saving moves behind `POST /chat/sessions/{id}/confirm` (pending action stored server-side with an id) - removes the regex confirmation (SEC-04, CA-09).
- LLM call happens before the DB write transaction (SEC-07); per-session Redis lock held for the turn (SEC-08).
- Session context writes go to Redis only; drop `_context_store` (CA-13).
- Session titles: schedule with a tracked background task; use `tier=fast`, `max_output_tokens=20`.

## 3. Failure-handling matrix
| Failure | Detection | Response |
|---|---|---|
| Missing/invalid API key (401) | startup check + 401 | Log once at error level, open circuit permanently until restart, run fallback mode, health endpoint reports `llm: "misconfigured"` |
| 429 rate limit | status 429 | Honour short `Retry-After`, else fallback immediately; counter metric `llm_rate_limited_total` |
| Timeout / connection error | `httpx.TimeoutException` | Retry up to max, then model fallback, then rules |
| 5xx | status >=500 | Same as timeout |
| Malformed JSON | parse/validate failure | One repair call, then rules; log schema error without content |
| Model returns disallowed keys/values | Pydantic `extra="forbid"` | Drop turn to clarification question |
| Budget exceeded | guard | 429 with friendly message for chat; rule-based for background features |
| Provider outage (circuit open) | breaker | `degraded: true`, canned/rule replies, UI banner |
| Prompt injection attempt | n/a (cannot detect reliably) | Defence by design: delimiters, schema validation, server-side confirm, no model-chosen IDs |

## 4. Test plan (no live calls in CI)
| Layer | Cases |
|---|---|
| Unit - `groq_provider` with `httpx.MockTransport` | 200 happy path with usage; 429 then 200 (retry honoured, sleep patched); 429 with long `Retry-After` -> `LLMRateLimited`; timeout x3 -> `LLMTimeout`; 500 x3 -> `LLMUnavailable`; 401 -> no retry; malformed body -> `LLMBadOutput`; request body assertions (model env mapping, `max_tokens`, `response_format`, no secrets in logs). |
| Unit - `json_utils` | fenced JSON, trailing text, wrong enum, extra key, repair success, repair failure. |
| Unit - `guard` | budget increment and TTL (fakeredis), exceed -> error, concurrency cap, circuit open/half-open/close with injected clock. |
| Unit - `fallbacks` | regex phone/email/date extraction (EN/TA digits), keyword intent table. |
| Integration - chat API with `FakeLLMProvider` | add contact full flow; missing field question; confirm via endpoint; cancel; "yes" text does not save; bad stage from model -> clarification, no 500; provider timeout -> degraded reply, messages persisted; budget exceeded -> 429; concurrent confirm -> one row. |
| Event-loop test | fake provider `await asyncio.sleep(2)`; `/api/health` p99 < 100 ms during 5 parallel chats. |
| Contract | recorded Groq response fixtures in `backend/tests/fixtures/groq/*.json` (captured once manually, scrubbed). |
| Eval set | `backend/tests/eval/utterances.yaml` ~40 items (EN/TA/Tanglish) with expected intent + fields; run manually against live Groq with `pytest -m live` (excluded from CI) to compare models and prompt versions. |

## 5. Rollout steps
1. [ ] Phase 0 fixes merged (rate limits, validation, failure path) - the provider swap is much riskier without them.
2. [ ] Create `services/llm/` with interface, fake provider and `bedrock_provider` wrapping current code; route every call site through it; behaviour unchanged; tests green.
3. [ ] Make orchestrator and callers `async`; remove `to_thread` shims; move prompts into `prompts.py`; add Pydantic result models and `fallbacks.py`.
4. [ ] Implement `groq_provider` + `guard` + config; unit tests with mocked transport.
5. [ ] Add confirm endpoint + frontend card change; remove text-based saving.
6. [ ] Manual evaluation on the utterance set with Groq vs Bedrock baseline (intent accuracy, field F1, p50/p95 latency, tokens per turn). Pick models (per 08). Record results in `STATUS.md`.
7. [ ] Set `LLM_PROVIDER=groq` in dev compose, run Playwright smoke, then default in `.env.example`.
8. [ ] Keep `bedrock_provider` for one release as rollback (`LLM_PROVIDER=bedrock` needs AWS creds).
9. [ ] Delete `bedrock_service.py`, `bedrock_provider.py`, `boto3` from `requirements.txt`, AWS vars; archive `docs/Bedrock_guide.md`; update `docs/architecture.md`, `docs/docker.md`, `docs/API.md`; `FIXES.md`/`STATUS.md` entries.

Rollback: set `LLM_PROVIDER=fake`-style rule mode (`LLM_ENABLED=false`) for instant degrade, or `bedrock` (until step 9).

## 6. Open questions `[?]`
- Exact Groq model ids, context windows, JSON-schema support, free-tier RPM/TPM/day limits, and data-retention/training terms: confirm in 08 and Groq docs before choosing budgets.
- Whether the demo needs Tamil script quality that requires the `smart` tier.
- Whether Groq has any region/data-residency option relevant to DPDP; if not, document the transfer in the privacy note and minimise payloads (pre-extraction, no full histories).

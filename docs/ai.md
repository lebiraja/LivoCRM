# AI Layer

Code: `backend/app/services/bedrock_service.py` (dispatch), `backend/app/services/llm/` (Groq client and
key pool), `backend/app/services/ai_engine/` (chat brain), `draft_service.py`, `session_naming.py`,
`lead_scoring.py`. Architecture context: `docs/architecture.md`.

## Providers

`LLM_PROVIDER` selects the backend. Every LLM call goes through `chat_completion()` in
`services/bedrock_service.py`, which dispatches on the setting.

| Value | Path | Requirements |
|---|---|---|
| `groq` (default) | `llm/groq_client.groq_chat` to `POST {GROQ_BASE_URL}/chat/completions` | `GROQ_API_KEYS` (or `GROQ_API_KEY`) |
| `bedrock` (legacy) | boto3 `converse` on `BEDROCK_LLM_MODEL` | AWS credentials, `BEDROCK_ENABLED=true` |

With no key configured, the Groq path raises `GroqServiceError` at once and every caller uses its fallback.
The lead scorer does not use an LLM. It runs a local RandomForest (`docs/architecture.md` section 7).

Bedrock is still in the code. `groq_client` imports `BedrockServiceError` from `bedrock_service`, and that
module imports `boto3` at load. Removing Bedrock is deferred.

## Models

| Setting | Default | Used by |
|---|---|---|
| `GROQ_MODEL_FAST` | `openai/gpt-oss-20b` | intent classification, field extraction, questions, confirmation text, general chat, chat titles, follow-up drafts |
| `GROQ_MODEL_SMART` | `openai/gpt-oss-120b` | dashboard insights only (`get_insights` passes `model_id`) |

Both models answered live on the account when the Groq path was built (`STATUS.md`, v0.3.0). That check was
not repeated for this document. Verify the model ids in the Groq console before a demo.

## Request shape

```text
POST {GROQ_BASE_URL}/chat/completions
Authorization: Bearer <key>
{ model,
  messages: [system, ...history],   history: leading assistant turns dropped,
                                    same-role neighbours merged, never empty
  max_completion_tokens: max(req, 512),
  temperature,
  reasoning_effort: "low",
  include_reasoning: false }
```

- `max_completion_tokens` has a floor of 512. `gpt-oss` spends part of the budget on reasoning, so a small
  cap returns empty text.
- Timeouts: connect 3 s, total `LLM_TIMEOUT_S` (default 15 s).
- Calls are synchronous (`httpx.Client`) and run inside `asyncio.to_thread`, gated by `llm_slots`, a
  process-wide semaphore of 8.
- Output is free text that the caller parses. Strict `json_schema` output is deferred. Callers strip Markdown
  fences, call `json.loads`, and fall back if parsing fails.

## Key pool

`KeyPool` (`services/llm/key_pool.py`) holds one entry per key. A key is identified by the first 8 hex
characters of its SHA-256. The secret leaves the module only in the `Authorization` header.

`GROQ_API_KEYS` is split on commas. `GROQ_API_KEY` is appended. Blanks and duplicates are dropped.

State is tracked per (key, model), because Groq limits apply per model.

Selection (`acquire`):

1. Skip a key that is in cooldown or disabled for that model.
2. Pick the key with the most remaining tokens. An unknown count counts as full, so a fresh key goes first.
3. Break ties by least recently used.

Outcome handling (`_attempt`):

| Result | Action |
|---|---|
| 2xx | Read `x-ratelimit-remaining-tokens` and `-requests`; clear cooldown; return text |
| 429 | Cooldown = `Retry-After` (Groq durations such as `2.5s`, `1m26.4s`, `120ms`, or plain seconds); default 20 s. Remaining tokens set to 0. Try the next key |
| 401 or 403 | Disable the key for **all** models for 3600 s. Try the next key |
| 408, 498, 5xx, timeout, transport error | Try the next key. No cooldown |
| other 4xx | Raise at once. No failover |

Per call, the client makes at most `min(keys + 1, 4)` attempts. If no key is free, it waits up to 2.0 s for the
earliest cooldown to end. A longer wait fails the call with "all Groq keys are rate limited or disabled".
That is the fallback path, and it keeps the request fast.

Limits and caveats:

- **Per organisation.** Groq limits are per organisation. Keys from one organisation share one bucket, so
  a second key from the same organisation adds no throughput. Keys from different organisations do.
- **Observed account limits:** 8,000 tokens per minute and 1,000 requests per day (`STATUS.md`). `HANDOVER.md`
  estimates roughly 2 to 3 chat turns a minute at 8,000 TPM. The per-user chat rate limit (30 per minute) is
  above that, so the provider limit is the binding one.
- **Daily limit.** The pool does not count requests against the 1,000 RPD budget. When Groq returns 429
  with a long `Retry-After`, that key cools down for that long. The call then fails fast and falls back.
- **Per process.** Pool state lives in memory. Restarting the backend resets it. Sharing state through Redis
  is deferred.
- **Secrets.** Logs record key id, model, status and retry delay. Prompts, completions and keys are never logged.

## Health endpoint

`GET /api/ai/health` (Bearer auth) reports the pool with no secrets:

```json
{
  "provider": "groq",
  "keys": 3,
  "pool": [
    {
      "key_id": "a1b2c3d4",
      "models": {
        "openai/gpt-oss-20b": {
          "state": "ready", "cooldown_s": 0.0, "remaining_tokens": 7412,
          "remaining_requests": 981, "calls": 12, "rate_limited": 0
        }
      }
    }
  ]
}
```

`state` is `ready`, `cooling` (cooldown active) or `disabled` (401/403 hold). The Settings page renders
this. The key-id value above is illustrative.

## Deterministic fallbacks

Every LLM call site catches `BedrockServiceError`, the base class of `GroqServiceError`, and degrades.
Nothing in the CRM depends on the model to save data, but chat creation does depend on classification.

| Call site | Model / temperature | Fallback |
|---|---|---|
| Intent classification (`intent_classifier.py`) | fast / 0.0 | `GENERAL_CHAT`, confidence 0. Unparseable JSON does the same |
| Field extraction (`data_extractor.py`) | fast / 0.0 | Returns the fields already collected. Nothing new is added |
| Follow-up question (`question_generator.py`) | fast / 0.7 | `Could you provide the <field description>?` |
| Confirmation summary (`orchestrator.py`) | fast / 0.3 | Bullet list of fields plus `Does this look correct? (yes/no)` |
| General chat (`orchestrator.py`) | fast / 0.7 | Static Livo greeting listing what it can do |
| Chat title (`session_naming.py`) | fast / 0.3 | First four words of the first message (max 50 chars) |
| Follow-up draft (`draft_service.py`) | fast / 0.3 | Built-in English and Tamil templates. Prompt holds purpose and IST time only, never the patient's name |
| Dashboard insights (`bedrock_service.py`) | smart / default | `generate_fallback_insights` (three sentences from the metrics). `generated_by: "fallback"` |

Consequence: with no key, every chat message classifies as `GENERAL_CHAT`. The assistant answers with the
greeting and cannot create or update records. Use the forms for those.

## Prompts and untrusted input

Prompts live in `services/ai_engine/prompts.py`. The user's message and up to 4 history turns go into the
extractor and classifier prompts without delimiters. Model output is treated as untrusted before any write:
it must validate against `ACTION_MODELS` (`extra="forbid"`), the extractor keeps only schema keys, and
targets resolve by exact name. Prompt-injection hardening for the non-write paths is open (SEC-21, see
`docs/security.md`).

## Lead score

`services/lead_scoring.py` loads `backend/ml/model.pkl` once per process. The file is built at image build
time by `ml/generate_data.py` and `ml/train_scorer.py`. The model is a RandomForest with 100 trees over seven
features: `has_company`, `has_phone`, `has_email`, `tag_count`, `notes_length`, `activity_count` and
`days_since_last_activity`. It was trained on synthetic data. No real-clinic training has happened, so scores
show model output only, not a validated prediction.

## Deferred

From `STATUS.md` and `HANDOVER.md`:

- Strict `json_schema` (constrained) output. Parsing is still prompt-based.
- Redis-shared key-pool state. Each worker keeps its own.
- Bedrock removal. The code remains, and `boto3` is still a hard import.
- Daily token and request budget guard. The pool does not enforce the 1,000 RPD limit.
- Async `httpx.AsyncClient`. The sync client runs in a thread.
- Confirm endpoint for chat writes. Confirmation is still a free-text reply.
- Tamil and Tanglish output evaluation. No eval set exists in the repo.

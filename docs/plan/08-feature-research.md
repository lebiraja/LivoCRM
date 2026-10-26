# 08 - Feature Research

Purpose: pick Groq models per AI task, rank features for IA3 marks + startup value per hour, snapshot competitors, and list honest innovation ideas for a Tamil/English clinic follow-up CRM.
Date: 2026-10-26 | Status: complete (desk research; no API calls made, no customer interviews) | Author: research-agent
Legend: `[?]` = unverified or source conflict. **Inference** = my reasoning, not a source claim. All URLs accessed 2026-10-26 unless marked; items marked "(note 2026-10-11)" come from `/home/lebi/start-it-up/research/market/2026-10-11-w1-whatsapp-ai-automation.md` and were not re-fetched.
Related: implementation of the provider swap lives in `04-groq-migration.md`; Tamil typography and i18n findings in `06-ui-audit-and-research.md` section 4.4.

## 0. Repo facts that shape these recommendations

| Fact | Where | Consequence |
|---|---|---|
| LLM layer is AWS Bedrock Converse via sync `boto3`; default model `us.meta.llama4-scout-17b-instruct-v1:0` | `backend/app/services/bedrock_service.py`, `backend/app/config.py:24` | Every caller goes through `chat_completion()`, so one provider module swap covers all AI paths |
| `process_message()` is sync and called directly inside an async route | `backend/app/routers/chat.py:203` | Up to 3 sequential LLM calls block the event loop per message; Groq migration should use `AsyncGroq` (or `asyncio.to_thread`) |
| JSON is parsed by stripping code fences and `json.loads` | `ai_engine/intent_classifier.py:63-75`, `ai_engine/data_extractor.py:76-103` | Replace with Groq strict structured outputs; removes the parse-failure fallbacks |
| Lead score = RandomForest trained at image build on synthetic rows labelled by a hand-written formula | `backend/ml/generate_data.py:21-36`, `backend/ml/train_scorer.py:33`, `backend/Dockerfile` | Explainability is cheap (the formula is known); also say "synthetic" openly in the viva |
| `/ai/score` never passes `days_since_last_activity`, so the model always sees the default 30 | `backend/app/routers/ai.py:39-47` vs `services/lead_scoring.py:35` | Fix before showing explanations, or the explanation will expose it |
| `activities.type` CHECK allows only `call,email,meeting,note,task` | `backend/app/models/activity.py:41-44` | Reminders/WhatsApp/SMS need new tables or a migration widening the CHECK |
| No appointment, message, consent, audit or role tables | `backend/app/models/` | All clinic features below are new schema (Alembic 0008+) |
| Contact fields: name, email, phone, company, tags, notes, lead_score, source | `backend/app/models/contact.py` | Add `preferred_language`, `consent_*`; `source` CHECK must widen beyond `manual,ai_chat` |

## 1. Groq API (state on 2026-10-26)

### 1.1 Models available

| Model ID | Status | Context / max out | Price per 1M tokens (in / cached in / out) | Speed (Groq page) | Structured outputs | Notes |
|---|---|---|---|---|---|---|
| `openai/gpt-oss-20b` | Production | 131,072 / 65,536 | $0.075 / $0.037 / $0.30 | ~1000 tps | JSON object, JSON schema, strict | Tool use, browser search, code execution, reasoning (low/medium/high). MMMLU 75.7% |
| `openai/gpt-oss-120b` | Production | 131,072 / 65,536 | $0.15 / $0.075 / $0.60 | ~500 tps | JSON object, JSON schema, strict | Same feature set. MMMLU 81.3%. Apache-2.0 weights |
| `qwen/qwen3.8-27b` | **Preview** | 131,072 / 16,384 | $0.80 / - / $4.00 (unit not stated on page) [?] | ~450+ tps | JSON object, JSON schema, strict | Vision input; `reasoning_effort: "none"` disables thinking. Preview = "may be discontinued at short notice" |
| `meta-models/muse-spark-open`, `minimaxai/minimax-m2.7` | Preview, Enterprise | 131K / 196K | not checked | - | muse-spark: strict | Enterprise-only per models page; ignore for a student account |
| `llama-3.1-8b-instant`, `llama-3.3-70b-versatile` | Listed under Production with "Enterprise" note; **shut down 2026-08-16 for free/developer tiers** | 131K | - | - | - | Deprecations page: replacements `gpt-oss-20b` and `gpt-oss-120b`. Any old tutorial using these will fail |
| `whisper-large-v3` | Production (STT) | 100 MB file (25 MB free tier) | $0.111 per audio hour | - | - | Transcription + translation-to-English; avg WER 10.3% (Groq page) |
| `whisper-large-v3-turbo` | Production (STT) | same | $0.04 per audio hour | - | - | Transcription only, no translation; avg WER 12% |
| `canopylabs/orpheus-v1-english` | Preview (TTS) | - | - | - | - | English only; no Tamil TTS on Groq |

Also gone (deprecations page): `meta-llama/llama-4-scout-17b-16e-instruct` (2026-07-17), `llama-4-maverick` (2026-03-09), `qwen/qwen3-32b` (2026-07-17), `moonshotai/kimi-k2-instruct-0905` (2026-04-15), `groq/compound` and `compound-mini` (2026-09-21), `qwen/qwen3.6-27b` (2026-09-14). The Bedrock default in this repo is a Llama 4 Scout variant; its Groq equivalent no longer exists.

Sources: https://console.groq.com/docs/models ; https://console.groq.com/docs/deprecations ; https://console.groq.com/docs/model/openai/gpt-oss-20b ; https://console.groq.com/docs/model/openai/gpt-oss-120b ; https://console.groq.com/docs/model/qwen/qwen3.8-27b ; https://console.groq.com/docs/speech-to-text

### 1.2 API capabilities that matter here

| Capability | What Groq documents | Use in LivoCRM |
|---|---|---|
| OpenAI-compatible endpoint | `base_url = https://api.groq.com/openai/v1`; key from `GROQ_API_KEY`. Unsupported: `logprobs`, `logit_bias`, `top_logprobs`, `messages[].name`, `n != 1`; `temperature=0` is converted to `1e-8` | Either the `groq` SDK (`AsyncGroq`) or `openai` SDK works. Do not request logprobs for "confidence"; ask for a confidence field in the schema instead |
| Structured outputs (strict) | `response_format: {type: "json_schema", json_schema: {..., strict: true}}` on gpt-oss-20b/120b, qwen3.8-27b, muse-spark. Strict rules: **every property in `required`**, optional fields as `["type","null"]`, **`additionalProperties: false` on every object**. **Streaming and tool use are not supported together with structured outputs** | Intent + extraction schemas from `ai_engine/prompts.py` must be rewritten: optional CRM fields become nullable-required. Keep chat replies (streamed) separate from extraction calls |
| Tool use | Supported on gpt-oss models | Option for QUERY_DATA (`count_contacts`, `list_due_reminders`); not needed for the core flow |
| Reasoning controls | gpt-oss: `reasoning_effort` low/medium/high (no "none"), `include_reasoning: false` hides it from the response; `reasoning_format` unsupported. Qwen 3.8: `reasoning_effort: "none"` turns thinking off | Use `low` for classification/extraction. Whether hidden reasoning tokens are billed as output is not stated on the reasoning page [?]; assume yes when budgeting |
| Speech-to-text | `/openai/v1/audio/transcriptions` and `/translations`; `language` (ISO-639-1, e.g. `ta`), `prompt` up to 224 tokens for spellings, `verbose_json` for segment/word timestamps; min billed 10 s; formats flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, webm | WhatsApp voice notes are ogg/opus: accepted format. Pass `language="ta"` and a prompt with clinic/doctor names |

Sources: https://console.groq.com/docs/openai ; https://console.groq.com/docs/structured-outputs ; https://console.groq.com/docs/reasoning ; https://console.groq.com/docs/speech-to-text

### 1.3 Rate limits, tiers, pricing, latency

| Item | Value | Source / confidence |
|---|---|---|
| Limits as rendered on the rate-limits page (gpt-oss-20b, gpt-oss-120b, qwen3.8-27b each) | 30 RPM, 1,000 RPD, 8K TPM, 200K TPD | https://console.groq.com/docs/rate-limits. The page has Free/Developer tabs and a sentence calling the shown limits "base limits for the Developer plan"; the text fetch could not tell which tab rendered [?]. These figures match Groq's historical free-tier numbers. **Check https://console.groq.com/settings/limits for the real account** |
| Whisper limits | 20 RPM, 2,000 RPD, 7,200 audio-seconds/hour, 28,800 audio-seconds/day | same page |
| Scope | Per organization, per model. Cached tokens do not count toward limits | same page |
| Headers | `x-ratelimit-{limit,remaining,reset}-{requests,tokens}` on every response (requests = RPD, tokens = TPM); `retry-after` (seconds) only on 429 | same page |
| Developer tier | Card required; "significantly increased rate limits", chat support, Flex tier, Batch, spend limits. India billing address: progressive invoices at $1, $10, then every $100. No charge below $0.50 | https://console.groq.com/docs/billing-faqs |
| Flex tier | Paid only; same price, higher limits, fails fast with 498 `capacity_exceeded`; Groq recommends jittered backoff | https://console.groq.com/docs/flex-processing |
| Latency (independent) | gpt-oss-120b on Groq at **high** reasoning: median ~472 output t/s, first chunk 0.69 s, time to first *answer* token 4.85 s, 5.99 s for 500 tokens (72 h medians) | https://artificialanalysis.ai/models/gpt-oss-120b/providers. Cerebras and SambaNova were faster on that page. **Inference:** most of the 4.85 s is reasoning; use `low` effort for interactive calls and measure in-app |

**Budget (inference, my arithmetic):** one chat turn today = 3 calls (classify, extract, question/confirm; `01-code-audit.md` LLM call map). At ~2,500 input + ~600 output tokens per turn (reasoning included), gpt-oss-20b costs ≈ $0.00037/turn (≈ $0.37 per 1,000 turns); gpt-oss-120b ≈ $0.74 per 1,000 turns. A 60-second Tamil voice note on whisper-large-v3 ≈ $0.0019. Cost is not the constraint; **free-tier TPM is**: 8K TPM / ~3.1K tokens ≈ 2-3 chat turns per minute per model. Mitigations: merge classify + extract into one strict-schema call (3 calls -> 2), split tasks across 20b and 120b (limits are per model), cap `max_completion_tokens`, reuse a fixed system prompt so cached tokens apply, and pre-warm nothing during the viva. Upgrading to Developer tier before demo day removes the risk for a few cents.

### 1.4 Retry and backoff

| Status | Groq meaning | Action |
|---|---|---|
| 400 / 422 | Bad syntax / semantic error or "model hallucinations" | Do not retry 400. Retry 422 once, then fall back |
| 401 | Bad key | Fail fast, log, show deterministic fallback |
| 413 | Body too large | Trim history (keep last 4 messages, as the code already does) |
| 429 | Rate limit | Sleep `retry-after` seconds (header), else exponential backoff with jitter; then switch to the fallback model (separate per-model limit) |
| 498 | Flex capacity | Retry with jitter or drop to on-demand |
| 500 / 502 / 503 | Server / upstream / overloaded | Retry with backoff (500 is not charged) |

The `groq` Python SDK already retries connection errors, 408, 409, 429 and >=500 **2 times with short exponential backoff**; default timeout 60 s; `AsyncGroq` is the async client (https://github.com/groq/groq-python). Recommendation: set `max_retries=2`, `timeout=15` for interactive calls, then the app-level chain model A -> model B -> deterministic fallback (the repo already has this pattern in `generate_fallback_insights`, `bedrock_service.py`). Error table source: https://console.groq.com/docs/errors

### 1.5 Data retention and DPDP

| Point | Source claim | Implication (inference) |
|---|---|---|
| Default retention | "By default, Groq does not retain customer data for inference requests"; inputs/outputs may be logged up to 30 days for reliability/abuse investigations; usage metadata always kept | Patient names and phone numbers in prompts can sit in US logs up to 30 days unless ZDR is on |
| Zero Data Retention | Any customer can enable ZDR at console.groq.com/settings/data-controls; disables batch and fine-tuning | **Turn ZDR on** before any real clinic data; costs nothing for this use case |
| Location | Customer data stored in US-based Google Cloud buckets; SCCs offered for transfers | Cross-border transfer from India to the US |
| Training | Privacy policy (effective 2025-11-12) excludes GroqCloud customer data and defers to the Services Agreement and DPA; neither was read here [?] | Read the DPA before a paid pilot |
| DPDP Act 2023 + Rules | Rules notified 13/14 Nov 2025 with an 18-month phase-in; substantive duties (notice, consent, security, breach reporting) from ~13 May 2027. MeitY proposed cutting to 12 months (13 Nov 2026); **no notified amendment found** as of today [?]. Section 16 is a negative-list regime; no restricted countries notified; not yet in force | US processing is lawful today. Clinic = Data Fiduciary, LivoCRM = Data Processor, Groq = sub-processor. Penalties up to ₹250 cr per instance, no MSME exemption (Inc42 via note 2026-10-11) |
| Design rules for the build | (inference) | Send the LLM only what the task needs: first name, appointment time, clinic name; never diagnosis or notes. Keep the Bedrock-style deterministic fallback so the product works with AI off. Log consent per contact and purpose. No clinical advice in any generated message (safe-lane rule from `start-it-up` health note) |

Sources: https://console.groq.com/docs/your-data ; https://groq.com/privacy-policy ; https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf ; https://ssrana.in/articles/meity-plans-to-cut-short-dpdp-compliance-timeline-and-notify-cross-border-restrictions-for-sdfs/ ; https://www.legal500.com/developments/?p=53484 ; https://ksandk.com/data-protection-and-data-privacy/cross-border-data-transfers-dpdp-act-india/ ; https://www.mondaq.com/india/data-protection/1764976/from-localisation-debates-to-a-negative-list-making-cross-border-data-transfers-work-under-indias-dpdp-act

### 1.6 Tamil and Tanglish quality: what is and is not known

- No published Tamil score was found for gpt-oss-20b/120b or qwen3.8-27b. Groq quotes only an MMMLU average; the gpt-oss Hugging Face card names no languages (https://huggingface.co/openai/gpt-oss-120b). Indic benchmarks (MILU, IndicGenBench) predate these models (https://arxiv.org/abs/2411.02538 ; https://preview.aclanthology.org/setup/2024.acl-long.595).
- Whisper: Groq's WER figures are cross-language averages. Deepgram argues OpenAI's text normalisation understates Whisper's error on South Asian languages, including Tamil, by roughly 30% (https://deepgram.com/learn/how-openai-s-text-normalization-hides-whisper-s-true-word-error-rate-for-south-asian-and-southeast-asian-languages, updated 2024-06-13). Tamil fine-tunes report far lower WER but are not on Groq.
- **Action (inference):** build a 40-item eval set before choosing: 20 Tamil/Tanglish intent/extraction messages ("naalaiku 5 mani appointment venum, peru Kavitha"), 10 reply drafts, 10 voice notes recorded on a phone. Lebi scores outputs by hand (native speaker). Keep it in `backend/tests/fixtures/`; it also becomes viva evidence.

### 1.7 Recommendation per task

| Task | Primary | Fallback 1 | Fallback 2 | Settings | Why |
|---|---|---|---|---|---|
| Intent classification + field extraction (merged, one call) | `openai/gpt-oss-20b` | `openai/gpt-oss-120b` | keyword/regex rules -> `GENERAL_CHAT` | strict `json_schema`, `reasoning_effort: "low"`, `max_completion_tokens` ~400, temp 0.2 | Cheapest, fastest production model with strict schemas; separate rate-limit bucket from the fallback |
| Follow-up copilot: draft reminder / recovery message in Tamil, English, Tanglish | `openai/gpt-oss-120b` | `openai/gpt-oss-20b` | fixed bilingual templates with variables | `reasoning_effort: "low"`, temp 0.5-0.7, strict schema `{ta, en, tanglish, tone}` (no streaming needed) | Larger model, higher multilingual average (81.3% vs 75.7%); output is short and reviewed by staff before send |
| Persona chat replies (existing `GENERAL_CHAT`) | `openai/gpt-oss-20b` | `openai/gpt-oss-120b` | canned reply | stream, no schema, `include_reasoning: false` | Interactive; streaming cannot combine with structured outputs |
| Dashboard insights / weekly summary | `openai/gpt-oss-120b` | `openai/gpt-oss-20b` | existing `generate_fallback_insights` | strict schema `{insights: [string x3]}` | Low volume, quality matters more than speed |
| Session titles | `openai/gpt-oss-20b` | none | first 6 words of message | 30-token cap | Background, trivial |
| Speech-to-text (Tamil voice notes, recorded calls) | `whisper-large-v3` | `whisper-large-v3-turbo` | manual note | `language="ta"`, `prompt` with clinic/doctor names, `verbose_json` | Lower average WER; turbo is 2.8x cheaper but cannot translate. Tamil accuracy unverified |
| Optional experiment | `qwen/qwen3.8-27b` | - | - | `reasoning_effort: "none"` | Preview only: test on the Tamil eval set, never the default |

Env keys to add (names only): `GROQ_API_KEY`, `GROQ_MODEL_FAST`, `GROQ_MODEL_SMART`, `GROQ_STT_MODEL`, `AI_PROVIDER` (`groq|bedrock|off`). Implementation details belong in `04-groq-migration.md`.

## 2. Features

### 2.1 Channel economics and legal constraints (read before building reminders)

| Topic | Finding | Source |
|---|---|---|
| WhatsApp billing change, 1 Oct 2026 | Meta's pricing page now confirms it: per-message charges resumed for **service (free-form, in-window) messages after 1,000 free delivered per business number per month**, and for **utility templates sent inside the 24 h window** (previously free since 1 Jul 2025). Without a payment method, service messages stop after the free 1,000. Govt/non-profits stay free to 31 Dec 2027. This resolves the conflict flagged in the 2026-10-11 note (Meta's page then still said "free") | https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing |
| India rates (excl. 18% GST) | Marketing ₹0.8631, utility ₹0.115, authentication ₹0.115, service ₹0.115 after the free 1,000. Meta publishes India numbers only in CSV/PDF rate cards | note 2026-10-11 citing https://chatmaxima.com/whatsapp-api-pricing/india/ (secondary) [?] |
| What it costs a clinic (inference) | 1,500 utility reminders + 3,000 replies + 500 marketing ≈ ₹834 + GST/month at Meta rates; BSP subscriptions (₹2,400-4,000/month) cost 2-5x the messages | note 2026-10-11 |
| Getting on the API | Business verification, display-name approval, template approval, a number not on the WhatsApp app; INR billing mandatory for eligible Indian WABAs from 1 Jan 2027 | note 2026-10-11 (Meta updates page) |
| Meta AI rule | WhatsApp Business Platform terms bar "AI Providers" where AI is the primary function; a business's own support/booking bot is ancillary and allowed | note 2026-10-11 (https://www.facebook.com/legal/Meta-Terms-for-WhatsApp-Business-Platform) |
| TRAI / SMS | Commercial SMS needs DLT registration (entity, header, templates). Since Oct 2024, unwhitelisted URLs/callback numbers in SMS are blocked. The Feb 2025 TCCCPR amendment adds header suffixes (-P/-S/-T/-G), lets users complain about commercial messages from **unregistered 10-digit numbers**, and lets operators suspend or disconnect such senders | https://www.azbpartners.com/?p=82843 ; https://www.jsalaw.com/wp-content/uploads/2025/02/JSA-Prism-Telecommunications_February-2025_TCCCPR-amendments.Final_.pdf ; https://www.medianama.com/2025/05/223-suffixes-commercial-sms-headers-spam/ (secondary; TRAI text not read) [?] |
| Consequence for `sms_service_tool` (inference) | Lebi's Android gateway sends from a personal SIM, i.e. an unregistered 10-digit sender. Fine for a demo to consenting test numbers (Lebi's own phones); **not safe for bulk reminders to real patients** (SIM suspension risk). It is HTTP-polling with an atomic claim/lease, zero-auth, private network only (memory of that project), so LivoCRM should call it from the backend container over a private network, never expose it | `/home/lebi/.claude/projects/-home-lebi-projects-sms-service-tool/memory/smstool-architecture.md` |

**Safe demo channels (recommended):**
1. **Simulated channel** (default): messages go to an outbox table with status transitions (`queued -> sent -> delivered -> replied`) driven by a simulator; a "patient phone" panel in the UI shows them. Zero cost, zero legal risk, deterministic for the viva.
2. **wa.me click-to-chat link**: `https://wa.me/<countrycode+number>?text=<urlencoded>` opens the staff member's own WhatsApp with the message prefilled; a human presses send. No API, no Meta billing, no bulk sending. Format from WhatsApp's click-to-chat help page (https://faq.whatsapp.com/5913398998672934; page did not render in the fetch, format is from prior knowledge [?]).
3. **SMS gateway (`sms_service_tool`)**: live send to 1-2 consenting numbers during the demo to prove a real channel.
4. **WhatsApp Cloud API**: post-IA3, only for a paid pilot, through a BSP or direct with a verified business.

### 2.2 Ranked backlog

Scoring: **Rubric** = marks leverage across the six IA3 rubrics (1-5); **Startup** = value to the clinic follow-up desk demo (1-5); **Hours** = my estimate for Lebi with Claude agents, including migration, API, UI, tests (inference). **Score = (Rubric + Startup) / Hours.** Dependencies are listed; build order in 2.3 overrides pure score.

| ID | Feature | What it is | Why it matters | Rubric | Startup | Hours | Score | Depends on | Main risks |
|---|---|---|---|---|---|---|---|---|---|
| F1 | Consent + opt-out | `consent_whatsapp`, `consent_sms`, `consent_at`, `consent_source` on contacts; "STOP"/"நிறுத்து" reply flips it; sends blocked without consent | DPDP notice/consent and TRAI complaint risk; shows legal awareness in viva | 3 | 4 | 4 | 1.75 | - | Legal wording is not legal advice; keep it simple |
| F2 | Analytics extensions | No-show rate, reminder delivery/reply rate, response-time p50/p90, recovered ₹ by week | Fills the empty Analytics route with clinic metrics | 3 | 4 | 4 | 1.75 | F3, F6, F16, F18 | Small sample sizes look noisy; label periods |
| F3 | Response-time SLA timers | `received_at`, `first_response_at` on each inbound lead; live countdown chip (green < 5 min, amber < 30, red breach); p50/p90 on dashboard | Speed-to-lead is the startup's core promise; visible real-time UI in demo | 4 | 4 | 5 | 1.60 | Lead inbox (F14) for full value | Timer drift across tabs; compute server-side, render client-side |
| F4 | Follow-up copilot (Tamil/English/Tanglish drafts) | Button on contact/appointment: drafts a reminder or recovery message in 3 variants via Groq strict schema; staff edits, then sends via chosen channel | The "cutting-edge" item for Innovation; directly the startup's differentiator (Tamil quality) | 5 | 4 | 6 | 1.50 | Groq migration (F11) | Tamil quality unmeasured (see 1.6); must never give clinical advice; prompt-inject via patient names (sanitise) |
| F5 | No-show recovery workflow | Marking an appointment `no_show` creates a recovery task + drafted rebooking message; outcome tracked (`rebooked`, `declined`, `no_reply`) | The money moment for clinics; feeds recovered revenue | 4 | 5 | 6 | 1.50 | Appointments (F16), outbox (F18) | Attribution honesty (see F6) |
| F6 | Recovered-revenue dashboard | Card + chart: ₹ from appointments completed after a reminder or recovery message (no-show rebooked, missed call converted), against consult fee per appointment | The startup's headline metric; strong presentation slide | 4 | 5 | 6 | 1.50 | F5, F16, F18 | It is **attributed**, not causal; show "attributed" label and the rule |
| F7 | Lead-score explainability | Per-contact "why 72/hot": top 3 feature contributions from the known formula or RF perturbation, plus fix of the missing `days_since_last_activity` | Turns a black-box number into a defensible viva answer | 4 | 2 | 4 | 1.50 | - | Model is trained on synthetic data; say so |
| F8 | PWA | Manifest + service worker (installable on the front-desk Android phone), offline read of today's list | Mobile story for small clinics | 3 | 3 | 4 | 1.50 | - | Stale cache after deploys; keep offline scope to read-only |
| F9 | Tamil voice-note to activity (Whisper) | Upload/record a voice note; transcribe with `whisper-large-v3` `language=ta`; save as activity; optional extraction into fields | Visible AI + Tamil; useful for front desk | 4 | 3 | 5 | 1.40 | F11 | WER on phone audio unknown; audio is personal data (retention) |
| F10 | Seeded demo / simulation mode | `make demo` or `POST /api/demo/seed` loads a fictional Coimbatore clinic: 120 patients, 2 weeks of appointments, missed calls, no-shows, Tamil names; "advance clock" button fires due reminders | Makes the viva deterministic; same seed is the startup sales demo | 4 | 4 | 6 | 1.33 | F16, F18 | Seeded data shown as real; label "DEMO DATA" in UI |
| F11 | Groq migration with strict schemas + fallback chain | Provider module replacing Bedrock; merged classify+extract call; async client | Prerequisite for F4 and F9; removes AWS cost and parse failures | 5 | 3 | 6 | 1.33 | - | Free-tier TPM in demo; schema rewrite for strict mode |
| F12 | CSV import/export | Contacts/appointments upload with preview, phone normalisation to E.164, de-dupe on phone; export filtered list | Clinics run on Excel/registers; onboarding blocker | 3 | 5 | 6 | 1.33 | - | Malformed files, Excel CSV encodings for Tamil (UTF-8 BOM) |
| F13 | Audit log | `audit_log(actor_id, action, entity, entity_id, before, after, at, ip)` written from service layer for create/update/delete and sends | DPDP evidence; backend rubric; `chat_actions` already does this for chat only | 3 | 3 | 5 | 1.20 | - | PII inside before/after diffs; redact phones |
| F14 | Lead / missed-call inbox | `POST /api/leads/inbound` (webhook-shaped; sources `missed_call`, `walk_in`, `web_form`, `whatsapp`) + inbox page with assign/respond; simulator posts fake missed calls | Captures the "never miss a lead" story; webhook shape is ready for an IVR/Exotel-style provider later | 4 | 5 | 8 | 1.13 | F3 | Real missed-call capture needs a telephony provider; demo is simulated |
| F15 | Tamil/English UI | Locale store + JSON catalogues for the main screens (~250 strings per `06` I1), Noto Sans Tamil, `en-IN` number grouping, per-contact `preferred_language` for messages | Startup differentiator; Front-end rubric | 4 | 5 | 8 | 1.13 | - | Layout breakage with longer Tamil strings (`06` I3); translation quality |
| F16 | Appointments | `appointments` table (contact, starts_at, fee_inr, status `booked/confirmed/completed/no_show/cancelled/rescheduled`, source); day/week list view; create from chat ("book Kavitha tomorrow 5pm") | Core clinic object; nothing else works without it | 5 | 5 | 10 | 1.00 | - | Timezone (store UTC, show IST); double-booking constraint |
| F17 | Role-based access | `users.role` (`owner`, `front_desk`, `viewer`) + workspace/clinic id; dependency `require_role` | Real clinics have a doctor and receptionist; viva security question | 4 | 3 | 8 | 0.88 | - | Today tenancy = one user; adding a clinic/workspace touches every query |
| F18 | Reminder scheduler + outbox | `messages` table (channel `simulated/wa_link/sms_gateway`, language, body, scheduled_at, status); worker loop in a second container from the same backend image using `SELECT ... FOR UPDATE SKIP LOCKED`; rules: T-24h and T-2h before appointment | The product itself; strong back-end integration evidence | 5 | 5 | 12 | 0.83 | F16, F1 | Duplicate sends (use idempotency key per appointment+rule); worker crash; quiet hours |
| F19 | WhatsApp Cloud API (real) | Template send + webhook receive | Production channel | 2 | 4 | 16+ | 0.38 | F18, F1 | Meta business verification, template approval, billing (2.1); not doable reliably before IA3 |

IDs are ordered by score (quick wins first). F11, F16 and F18 score lower but are prerequisites for most of the clinic story; section 2.3 sets the build order.

### 2.3 Build order (dependency-aware, inference)

| Phase | Items | Hours (est.) | Demo after this phase |
|---|---|---|---|
| A. Foundation | F11 Groq migration, F7 explainability fix, F1 consent fields | ~14 | Chat works on Groq with strict JSON; lead score explained |
| B. Clinic spine | F16 appointments, F18 outbox + worker (simulated + wa.me first, SMS gateway last), F10 demo seed | ~28 | Book, auto-remind, see messages on the simulated phone |
| C. Recovery story | F14 lead inbox, F3 SLA timers, F5 no-show recovery, F6 recovered revenue, F2 analytics | ~29 | Full "missed call -> response -> booking -> no-show -> recovery -> ₹ recovered" narrative |
| D. Differentiators | F4 copilot, F15 Tamil UI, F9 voice notes | ~19 | Tamil end to end |
| E. Hardening | F13 audit log, F17 RBAC, F12 CSV, F8 PWA | ~23 | Owner vs front-desk login; import a clinic's Excel |

Total ≈ 113 h (estimate). If time is short, cut E except F13 audit log, then F9 and F8.

## 3. Competitor snapshot

All prices are vendor or third-party listing claims, unverified by purchase. INR excl. GST unless stated.

| Product | What it is | Price (claim) | Strengths | Gaps relevant to a Tamil clinic follow-up desk | Source |
|---|---|---|---|---|---|
| Bigin by Zoho CRM | Pipeline CRM for small businesses (Indian vendor) | Express ₹400, Premier ₹720, Bigin 360 ₹1,080 per user/month annual (vendor clarification page); a Zoho partner lists Free (3 users), ₹420, ₹840 [conflict] | Mature, cheap, mobile apps, WhatsApp/telephony integrations through the Zoho ecosystem | Generic sales pipeline, not appointments/no-shows; setup left to the owner; Tamil message quality not checked [?] | https://www.bigin.com/articles/bigin-india-pricing-clarification.html ; https://precisiontech.in/software/zoho/zoho-bigin/ |
| Kylas | Indian SMB sales CRM | Free "Embark"; "Elevate" ₹12,999/month flat, unlimited users (vendor); third party shows ~$250/month [conflict] | Flat pricing, unlimited users | Sales-team oriented; price far above a single-doctor clinic | https://kylas.io/kylas-vs-leadsquared ; https://gappsy.com/tools/kylas/ |
| Interakt (Jio Haptik) | WhatsApp BSP + Sales CRM | Growth ₹2,799/month, Advanced ₹3,799, Sales CRM ₹2,499 (+₹499/agent), AI agent ₹3,000 add-on (fetched 2026-10-11) | Official BSP, broadcasts, catalogues | Trustpilot 1.9 (13 reviews): support, refunds, number blocks; DIY setup | note 2026-10-11: https://www.interakt.shop/pricing/ ; https://www.trustpilot.com/review/interakt.shop |
| Wati | WhatsApp BSP, inbox, AI agents | ₹999 one-time PAYG single user; higher plans not shown in INR (fetched 2026-10-11) | Widely used, AI credits bundled | Trustpilot 3.0, Indian reviewers cite support and downtime | note 2026-10-11: https://www.wati.io/pricing/ ; https://www.trustpilot.com/review/wati.io |
| AiSensy | WhatsApp BSP for SMBs | Free plan + add-ons; AI agent ₹1,215-1,350/month; utility/service ₹0.145 per message (fetched 2026-10-11) | Cheap entry, 20% recurring partner commission (a channel for Lebi) | Trustpilot 3.4; "support is name sake"; no Tamil UI seen | note 2026-10-11: https://www.aisensy.com/pricing ; https://www.aisensy.com/partner |
| Ray by Practo | Clinic management (EMR, billing, scheduling) | No price on product page; listings say ₹999/month or "$15" [conflict]; 7-day free trial | Brand, EMR + billing + online payments, "automated appointment SMSes" | Product page mentions SMS, not WhatsApp; no patient recall listed; no language info | https://www.practo.com/providers/clinics/ray ; https://us.fitgap.com/products/ray-by-practo ; https://www.capterra.in/software/167778/ray |
| Clinizy Care / Qare (small-clinic apps) | Clinic software with WhatsApp reminders and recall | Clinizy Essentials ₹1,999/month or ₹19,999/year (1 doctor, 3 staff); Qare from ₹1,999 (listings) | Reminders + recall bundled with clinic records at SMB price | Aggregator data only, few or no reviews; Tamil not confirmed; DIY | https://www.getapp.co.uk/software/2291297/clinizy-care ; https://www.getapp.ie/software/2083678/qare-1 |
| Edesy | Chennai/TN AI receptionist + WhatsApp bots, Tamil + English | Custom; voice plans ₹1,499-14,999/month (via earlier note) | Closest local competitor; Tamil; targets clinics | SEO-led site, anonymous testimonials; no traction data | note 2026-10-11: https://edesy.in/ai-receptionist/in/chennai |

**Pattern (inference):** reminders are already a bundled feature in ₹1-4k/month tools, so "sends WhatsApp reminders" is not a differentiator. Gaps that recur across sources: (a) setup and phone support (review complaints), (b) Tamil-first message quality, (c) an outcome number the owner understands ("₹ recovered this month") rather than message counts, (d) speed-to-lead accountability. The IA3 build should demo (b), (c) and (d); (a) is a service, not code.

## 4. Innovation ideas (honest and demoable)

| Idea | What the examiner sees | Honest framing for the viva | Hours | Backlog link |
|---|---|---|---|---|
| Explainable lead score | Score chip opens "why": 3 contributing factors with +/- weights, and what would raise the score | "RandomForest on synthetic data; explanation uses feature contributions; real data would retrain it" | 4 | F7 |
| Follow-up copilot in Tamil/Tanglish | Click "Draft" on a no-show: three variants appear in under ~2 s; staff edits; consent check gates the send | "LLM drafts, human sends; no clinical content; structured output guarantees the fields" | 6 | F4 |
| SLA timers with breach escalation | Inbound missed call arrives via simulator; red countdown starts; WebSocket pushes it to the dashboard live | "Measures response time, the metric clinics lose money on" | 5 | F3 (uses the existing unused dashboard WS) |
| Simulation mode with a clock | "Advance 24 h" button fires reminders, simulated patients reply, no-shows trigger recovery | "Deterministic demo of an event-driven system; real channels plug into the same outbox" | 6 | F10 |
| Recovered-revenue ledger | Every ₹ in the headline links to the appointment and message that earned it | "Attribution rule shown on screen; not a causal claim" | 6 | F6 |
| Channel-agnostic outbox | Same message routed to simulated / wa.me / Android SMS gateway by a setting; live SMS to Lebi's phone in the demo | "Adapter pattern; WhatsApp API is a fourth adapter later" | in F18 | F18 |
| Tamil voice note to CRM fields | Record "Kavitha, naalaiku 5 mani, pal vali" -> transcript -> extracted appointment | "Whisper large-v3 on Groq; Tamil accuracy measured on our own 10-clip set: X%" (report the real number) | 5 | F9 |
| AI cost and privacy meter | Settings page shows tokens used, ₹ estimate, model used per call, ZDR status, PII fields withheld | "Responsible AI: we send the minimum data" | 3 | new |

Avoid claiming: "AI predicts no-shows" (no real data), "HIPAA/DPDP compliant" (needs legal review), "real WhatsApp integration" (unless actually shipped).

## 5. Gaps and open items

- Free vs Developer rate-limit tab not confirmed [?]; check the account's limits page.
- No Tamil benchmark for any Groq LLM; Tamil Whisper WER unmeasured. Run the eval in 1.6 before claiming quality.
- Whether gpt-oss hidden reasoning tokens are billed is not stated on Groq's reasoning page [?].
- Groq DPA and Services Agreement not read.
- DPDP 12-month compression: proposal only; re-check MeitY/Gazette before 13 Nov 2026.
- TRAI Feb 2025 amendment read through law-firm summaries, not the regulation PDF.
- India WhatsApp per-message rates are secondary (Meta publishes them only as CSV/PDF).
- Competitor pricing for Bigin, Kylas and Ray conflicts across sources; none bought or demoed.
- Hour estimates are mine and untested.

# LivoCRM → IA3 (Full Stack + Cloud): Master Implementation Plan

Date: 2026-10-26 · Owner: Lebi · Repo: `/home/lebi/Projects/sem5/full-stack/LivoCRM` · Status: approved 2026-10-26, execution started

## Context

LivoCRM (FastAPI + React/Vite + Postgres + Redis + Nginx, Docker) was cloned as the base for **two** graded IA3 submissions with one codebase:

1. **Full Stack Development IA3** (30 marks: front end, back end, functionality, presentation, innovation, documentation). Faculty approved this stack.
2. **Cloud Computing IA3** (25-mark project + certificate). Rubric needs: real problem in Food/Health/Water/Energy, dataset from cloud storage, **Docker + serverless function + ETL + CI/CD (10 marks)**, managed cloud ML + dashboard, report with <10% plagiarism. **Provider chosen: AWS.** Domain: **Health** (clinic no-show / missed-lead recovery).

It also doubles as the demo for Lebi's startup idea (Tamil/English follow-up desk for clinics).

Three agents already produced the research: `docs/plan/01..09` (audit: 29 security + 31 code findings, no tests/CI; UI audit and "Ledger" design; Groq and feature research; rubric mapping). This plan turns those into one ordered, gated build. **Stack does not change.** Deadline: "as soon as possible", so every phase ends in a demo-able build and a git tag.

## Locked decisions

| Topic | Decision |
|---|---|
| Stack | FastAPI, React 19/Vite 8/TS strict, Tailwind 4 + shadcn/ui, Postgres 16, Redis 7, Nginx, Docker Compose, Alembic |
| LLM | Groq via httpx behind a provider interface; Bedrock removed at cutover. Models from env only: `openai/gpt-oss-20b` (fast), `openai/gpt-oss-120b` (smart), `whisper-large-v3` (STT). **Verify names + limits in the Groq console before coding (limits tab unverified).** |
| Groq keys | **1 key works; up to 4+ keys load-balanced** (see Phase 1B) |
| Product | Clinic follow-up / no-show / missed-lead recovery, EN + TA, simulated channel by default |
| Cloud | AWS: EC2 + Compose, ECR, S3, Lambda, EventBridge, SageMaker, Athena + QuickSight, GitHub Actions (OIDC), SAM |
| Git | New private repo (not `lebiraja/LivoCRM`, which was the DBMS submission); branches `ia3/<phase>-<topic>`, conventional commits |
| Process | Failing test first. Every fix → `FIXES.md`; every phase → `STATUS.md`, `CHECKLIST.md`, `VERSIONS.md`, `HANDOVER.md`. `docs-keeper` agent owns `docs/`. |

## Execution model (fast)

Three parallel tracks after Gate 0, each in its own git worktree via `implementer` agents, merged at gates:

- **Track A, backend:** Phase 0 → 1 → 2.
- **Track B, frontend:** Phase 3 (builds on mocked/MSW API, wired to real API at Gate 2).
- **Track C, cloud:** Phase 6 ML/ETL work needs only a public dataset and Lambda/SAM, so it starts right after Gate 0 and joins the app at Gate 4.

`debugger` for failures, `test-writer` for coverage gaps, `e2e-runner` for Playwright, `logger` for STATUS/FIXES, `docs-keeper` per gate.

## Phase 0: Foundation and stop-ship fixes (Gate 0, ~28 h)

Source of truth: `docs/plan/02-security-review.md`, `03` Phase 0. Order matters.

| # | Task | Files | Done when |
|---|---|---|---|
| 0.0 | Plan copied to `docs/plan/00-master-plan.md`; new repo + remote; branch strategy | repo root | Plan in repo, `git remote -v` is the new repo |
| 0.1 | Test harness: pytest, pytest-asyncio, httpx `AsyncClient`, fakeredis, `FakeLLMProvider`, test DB profile, `requirements-dev.txt`, ruff, mypy | `backend/tests/conftest.py`, `backend/pytest.ini`, `docker-compose.yml` (`test` profile) | `docker compose run --rm backend pytest` green on a health smoke test |
| 0.2 | SEC-01: remove published `db` port, pgAdmin to dev profile on 127.0.0.1, rotate all committed passwords (Lebi action), `change-me` placeholders, gitleaks pre-commit | `docker-compose.yml`, `.env.example`, `docs/pgadmin_setup.md` | `docker compose config` has no host port for `db`; gitleaks clean |
| 0.3 | SEC-02/07: async-safe AI calls (interim `to_thread` + boto3 timeouts), release DB connection before LLM, semaphore | `routers/chat.py:203`, `services/bedrock_service.py` | `/api/health` <100 ms during 5 slow chats |
| 0.4 | SEC-03/12: Redis rate limiter dependency (login 5/min, register 3/h, chat 30/min, insights 10/h), nginx `limit_req`, `--proxy-headers`, password policy, lower-cased unique email (migration), dummy-hash timing fix | `services/rate_limit.py`, `routers/auth.py`, `nginx/nginx.conf`, `alembic/versions/0008_*` | 6th login → 429 + `Retry-After` |
| 0.5 | SEC-04/05/06/08/15: negation-safe confirmation (interim), per-intent Pydantic action models, `begin_nested()` save path, `failed` status migration, per-session Redis lock, publish after commit | `ai_engine/orchestrator.py:279-348`, `schemas/ai_actions.py`, `routers/chat.py` | "no, don't save" saves nothing; bad stage → friendly reply, no 500; concurrent confirms → 1 row |
| 0.6 | SEC-09/14/22: `require_owned()` FK checks, `Literal`/`Decimal`/length validation, `IntegrityError`→409, `DataError`→422, invalid `sub`→401 | `services/ownership.py`, `schemas/*`, `main.py` | Invalid enum → 422; foreign contact id → 404 |
| 0.7 | SEC-10/11/16/19/20: PyJWT with `iat/jti`, one-time WS ticket, WS ownership check, Redis-only session context | `auth_service.py`, `routers/websocket.py`, `frontend/src/hooks/useWebSocket.ts`, `session_manager.py` | Raw JWT on WS rejected; ticket single-use |
| 0.8 | SEC-13/17/18/23-28: PII-free logging, `.dockerignore`, non-root users, healthchecks + `service_healthy`, CSP and security headers, CORS from env, self-hosted fonts, Redis `requirepass`/maxmemory | Dockerfiles, `nginx/*`, `index.css` | `docker compose ps` all healthy; headers present |
| 0.9 | Delete dead code: `frontend/tmp-scaffold/`, unused ui/magicui files, `bedrock` leftovers noted; fix CA-quick wins (INR format, lead-score `days_since_last_activity`, `{{ }}` prompt braces) | see `01-code-audit.md` | `tsc -b` + eslint clean |

**Gate 0:** all Critical/High closed, pytest green, gitleaks clean, tag `v0.2.0-secure`, `FIXES.md` has one entry per finding.

## Phase 1: AI layer on Groq with a multi-key load balancer (Gate 1, ~34 h)

Design base: `docs/plan/04-groq-migration.md`. New package `backend/app/services/llm/` (`base.py`, `factory.py`, `groq_provider.py`, `key_pool.py`, `guard.py`, `json_utils.py`, `fake_provider.py`, temporary `bedrock_provider.py`) and `ai_engine/{prompts,schemas,fallbacks}.py`.

**1A. Provider and engine**
- 1.1 Provider interface + fake provider; route every call site through it (behaviour unchanged, tests green).
- 1.2 Async orchestrator/classifier/extractor; **merge intent + extraction into one strict-schema call**; deterministic pre-extraction of phone/email/date; all prompt text in `prompts.py`; untrusted text in delimiters; prompt version constant.
- 1.3 `groq_provider.py`: httpx `AsyncClient`, `response_format` strict `json_schema` (every property required, nullable optionals, `additionalProperties:false`), `reasoning_effort: low`, timeouts 3/15/20 s, retries 2 with jitter, usage accounting, no content in logs.
- 1.4 Guard: per-user daily token/request budget (Redis), input/output caps, concurrency semaphore, circuit breaker, `LLM_ENABLED` kill switch; user-visible `degraded: true`.
- 1.5 Real confirm/cancel endpoint `POST /api/chat/sessions/{id}/confirm`; saving only there; frontend card calls it.
- 1.6 Insights, titles, lead-score explanation via provider; fix `generated_by` leak.
- 1.7 Cutover: default `LLM_PROVIDER=groq`, run the 40-item EN/TA/Tanglish eval set, then delete `bedrock_service.py`, `boto3`, AWS vars, archive `docs/Bedrock_guide.md`.

**1B. Groq key pool (what you asked for)**

Config (`config.py`):
- `GROQ_API_KEYS` = comma-separated list (1 to N). `GROQ_API_KEY` stays as a single-key alias. Both parsed into `list[SecretStr]`, de-duplicated, empty rejected; startup fails loudly if provider is groq and no key. **One key = identical behaviour, no extra setup.**
- Keys are referenced everywhere by a **key id** = first 8 hex of SHA-256; the secret never appears in logs, errors, health output or tests.

`key_pool.py` behaviour:
1. **State** (Redis hash per key id and model, in-memory fallback if Redis is down): `cooldown_until`, `remaining_tokens`, `remaining_requests`, `reset_at` (read from `x-ratelimit-*` response headers), `consecutive_failures`, `disabled`.
2. **Selection** for each call (model chosen first): skip keys in cooldown or disabled; pick the key with the most known `remaining_tokens` (unknown counts as full); ties → least recently used. This spreads load evenly and avoids a key about to hit its per-minute token cap.
3. **429:** put that key+model in cooldown for `retry-after` (default 20 s), and **retry immediately on the next key** (no sleep). Attempts per request ≤ `min(keys + 1, 4)`.
4. **All keys cooling for a model:** if soonest reset ≤ 2 s, wait; else fall to the other model (limits are per model), then to rule-based fallbacks. Never block the event loop; never exceed the 25 s turn budget.
5. **401/403:** disable that key (retry in 1 h), keep serving with the others, surface in health.
6. **5xx/timeouts:** retry with jitter on the next key; circuit breaker stays per provider, not per key.
7. **Observability:** `GET /api/ai/health` (authenticated) returns per key id: state, cooldown seconds left, remaining tokens/requests, 24 h call count. No secrets. Shown in Settings as the "AI usage and privacy meter".
8. **Docs/runbook:** adding a key = append to `GROQ_API_KEYS` in `.env`, `docker compose up -d backend`. No code change.

Important caveats written into `docs/docker.md`:
- Groq rate limits are **per organization**, so keys from the same Groq org share one bucket and give no extra capacity. Extra capacity only comes from keys belonging to separate orgs/accounts.
- Using several free accounts to get around a vendor's limits may conflict with Groq's terms `[?]`. Read the terms; the clean alternative is the Developer tier, which costs cents at this volume. The pool is built to work either way.

Tests (`tests/llm/`, `httpx.MockTransport`, fakeredis, injected clock, no network): single key works; round-robin/least-remaining spread across 3 keys; 429 on key A → same request succeeds on key B without sleeping; all keys 429 → model fallback → rules; 401 disables one key only; cooldown expiry re-enables; header parsing updates remaining; key ids stable and secrets absent from logs/exceptions; concurrent calls do not double-select the last token; Redis down → in-memory pool; startup validation (empty, duplicates, whitespace).

**Gate 1:** chat works on Groq with 1 key and with 3 fake keys; no sync LLM call remains; eval results recorded; tag `v0.3.0-groq`.

## Phase 2: Domain pivot: clinic follow-up engine (Gate 2, ~40 h)

Base: `03` Phase 2 and `08` backlog F1, F3, F5, F6, F7, F10, F14, F16, F17, F18.

- 2.1 **Workspaces and roles:** `workspaces`, `memberships(owner|front_desk|viewer)`, move ownership from `user_id` to `workspace_id` with a backfill migration; `require_role()`; update every query and `ownership.py`.
- 2.2 **Data model (migrations 0009+):** `appointments` (UTC `timestamptz`, `fee_inr Decimal`, status booked/confirmed/completed/no_show/cancelled/rescheduled, exclusion constraint against double booking), `follow_up_tasks`, `message_templates` (EN/TA), `outbound_messages` (outbox with idempotency key), `leads` inbox (missed_call/walk_in/web_form/whatsapp; `received_at`, `first_response_at`), consent fields on contacts, `audit_log`; E.164 phone normalisation; indexes on `(workspace_id, due_at, status)` and `(workspace_id, phone)`.
- 2.3 **Recovery engine:** worker service (same backend image) with `FOR UPDATE SKIP LOCKED`; rules T-24 h and T-2 h reminders, no-show → recovery task, unanswered lead → follow-up; idempotent; injectable clock for tests.
- 2.4 **AI assist:** follow-up copilot drafts EN/TA/Tanglish (strict schema, human approves, consent-gated, minimal data to the LLM); inbound reply classifier (confirm/reschedule/stop).
- 2.5 **Channels:** `MessageChannel` interface with `SimulatedChannel` (default), `wa.me` link channel, and optional SMS-gateway adapter (consenting demo numbers only). Real WhatsApp API is out of scope.
- 2.6 **No-show risk score:** rules-based placeholder now; replaced by the SageMaker model in Phase 6 behind the same interface.
- 2.7 **APIs:** `appointments`, `follow-ups`, `templates`, `messages`, `leads`, `recovery/summary`, `ai/health`; response models everywhere; OpenAPI docs gated in prod.
- 2.8 **Seed/demo:** `python -m app.cli seed-demo` builds a Coimbatore clinic (3 users, ~120 patients, 2 weeks of appointments, missed calls, no-shows) and an "advance 24 h" simulation clock; seeded data labelled DEMO.

**Gate 2:** scenario runs end to end through the API: missed call → SLA timer → booking → reminders → no-show → drafted recovery → approval → logged send → recovered ₹ figure. Tag `v0.4.0-clinic`.

## Phase 3: Frontend redesign "Ledger" (Gate 3, ~34 h, parallel with Phase 2)

Source: `docs/plan/06`, `07` (design tokens, wireframes, acceptance criteria). Warm paper/ink, one deep-green accent, serif headings, ruled rows instead of card grids, mobile-first with bottom nav, EN/TA toggle with Noto Sans Tamil, `en-IN` number formatting.

- 3.1 Foundations: tokens (light + working dark), self-hosted fonts, Zod schemas for every API response, `useApi` with real error toasts, i18n catalogue (~250 strings), remove every fake fallback (Sarah Johnson insight, fake "Saved!", hard-coded user).
- 3.2 Screens: Today queue (approve/skip/snooze, keyboard-first), Leads + lead detail timeline, Pipeline with touch + keyboard moves, Assistant with real confirm card, Reports (recovered ₹, no-show rate, response-time p50/p90, SLA chips), Settings (working profile, templates, AI usage meter, language), Auth.
- 3.3 State: WebSocket reconnect fix, ticket auth, optimistic updates with rollback.
- 3.4 Accessibility and responsive: aria on dialogs and queue, focus rings, 360 px layouts, reduced motion; Tamil strings must not truncate.
- 3.5 HTML5/CSS3/Bootstrap/JS evidence: documented honestly in the report (semantic markup, CSS grid/flex/custom properties, a small Bootstrap-style utility mapping table, vanilla-JS hooks) without changing the stack (`07` §9).

**Gate 3:** `npm run build` clean under `strict`, zero `any`, Lighthouse mobile targets from `07` §8 measured (not guessed), tag `v0.5.0-ui`.

## Phase 4: Tests, CI, documentation (Gate 4, ~24 h)

- 4.1 **Backend tests** per `docs/plan/05`: auth ≥95%, mutations ≥90%, overall ≥80%; cross-tenant matrix; AI/LLM/key-pool suites; worker time-travel tests; regression test for every finding (`05` §7). Files under `backend/tests/{api,unit,services,ai,llm,worker}/`.
- 4.2 **Frontend tests:** vitest + Testing Library + MSW (stores, hooks, queue, confirm card, i18n); Playwright smoke in `e2e/` (login → approve follow-up → see logged send → switch to Tamil).
- 4.3 **CI** `.github/workflows/ci.yml`: ruff, mypy, pytest in compose, vitest, `tsc -b`, eslint, gitleaks, `pip-audit`, `npm audit`, compose config check, Playwright smoke.
- 4.4 **Docs (all current, `docs-keeper`):** create `docs/architecture.md`, `docs/docker.md`, `docs/API.md`, `docs/security.md`, `docs/testing.md`, `docs/ai.md` (providers, key pool, prompts, eval), new ER diagram + `DATABASE_SCHEMA.md`, `docs/runbook.md`; move `development_guide.md`, `walkthrough_problems.md`, `Bedrock_guide.md`, `dbms_academic_report.*`, old ER to `docs/archive/` with a note; refresh `README.md`.
- 4.5 **IA3 deliverables:** Full Stack report mapped to the six rubrics with a **reuse declaration** and delta table (base vs new, per file/feature); PPT; screenshots from the new UI; demo script (9 min) with fallback video (`docs/plan/09`).

**Gate 4:** coverage gates met, CI green, docs match the code. Tag `v0.6.0-docs`.

## Phase 6: Cloud Computing IA3 on AWS (Gate 5, ~30 h, Track C starts early)

Rubric map: dataset from cloud storage → Phase 6.2; **Docker + serverless + ETL + CI/CD (10 marks)** → 6.1, 6.3, 6.5; managed ML + dashboard → 6.4, 6.6; report → 6.7.

| # | Task | Detail |
|---|---|---|
| 6.1 | Deploy the same app | EC2 (t3.small/medium) running the compose stack behind Nginx with TLS (Caddy or certbot); images in **ECR**; Security Group allows 80/443 only; secrets (Groq keys, DB, JWT) in **SSM Parameter Store**; daily `pg_dump` to S3; AWS Budgets alarm at a small cap. RDS optional if free-tier eligible `[?]` |
| 6.2 | Dataset in S3 | Public Medical Appointment No-Shows dataset (Kaggle, ~110k rows, cite licence) uploaded to `s3://…/raw/`; plus nightly **anonymised** export of LivoCRM appointments (hashed ids, no names/phones, labelled synthetic or demo) to the same bucket; block public access, SSE, lifecycle rules |
| 6.3 | Serverless ETL | **Lambda** (S3 `ObjectCreated` + **EventBridge** schedule) validates, cleans, engineers features (lead time, weekday, hour, prior no-shows, reminder sent, age band) and writes Parquet to `curated/`; a second Lambda scores upcoming appointments nightly and posts `no_show_risk` back to the app API; infra as code with **AWS SAM** (`cloud/template.yaml`) |
| 6.4 | Managed ML | **SageMaker** training (built-in XGBoost, or Autopilot if credits allow) on the curated set; metrics (AUC, precision/recall) compared against a logistic-regression baseline in a notebook; model artifact in S3; the app's no-show risk chip and reminder priority consume it |
| 6.5 | CI/CD | **GitHub Actions** with OIDC role (no long-lived keys): test → build → push to ECR → deploy to EC2 via SSM Run Command → smoke test; separate job runs `sam build && sam deploy` for Lambdas |
| 6.6 | Dashboard | **Athena** over curated S3 + **QuickSight** dashboard (no-show rate by weekday/hour/lead-time, model metrics, recovery funnel); free-trial limits and cost to be verified `[?]`; fallback is the in-app Reports page plus exported screenshots |
| 6.7 | Cloud report | Separate report in Lebi's own words (plagiarism <10%): problem, architecture diagram (draw.io), pipeline, ML results, cost table, security, references; figures from the real deployment |

**Gate 5:** public HTTPS URL works from a phone; pipeline run end to end (upload → Lambda → Parquet → SageMaker metrics → score → app chip → QuickSight); CI deploys on merge. Tag `v1.0.0-ia3`.

## Phase 7: Polish, rehearsal, freeze (~10 h)

Remaining Low findings, `EXPLAIN` check of new indexes, small load smoke (`hey`) on 5 endpoints, deep `/api/health`, two full rehearsals (Full Stack demo and Cloud demo), offline fallback video, freeze and final tag.

## Effort and cut lines

| Phase | Hours |
|---|---|
| 0 Foundation/security | ~28 |
| 1 Groq + key pool | ~34 |
| 2 Clinic engine | ~40 |
| 3 UI | ~34 (parallel) |
| 4 Tests/CI/docs | ~24 |
| 6 AWS | ~30 (parallel) |
| 7 Polish | ~10 |
| **Total** | **~200 h of work; ~110-130 h calendar with three parallel tracks** |

Order of sacrifice if time runs out (never the first four): keep 0, 1, 2.1-2.3, 3.2 (4 core screens), 6.1-6.5 → then drop in this order: voice notes (not in scope here), PWA, CSV import, RBAC `viewer`, QuickSight (use in-app Reports), RDS, Playwright beyond smoke.

## Documentation and tracking rules (continuous)

- Every gate updates: `STATUS.md` (prepend entry), `CHECKLIST.md` (tick verified items only), `VERSIONS.md` (new row + tag), `HANDOVER.md` (current state and next step), `FIXES.md` (symptom, root cause, fix `file:line`, verification, finding id).
- `docs/plan/README.md` index gets `00-master-plan.md` first; plan docs 01-09 stay as the evidence base and are marked "implemented in vX" as phases close.
- `docs-keeper` runs at each gate; docs describe the code as built, not as planned.

## Verification (end to end)

1. `docker compose run --rm backend pytest --cov` and `docker compose run --rm frontend npm test`: green, coverage gates met.
2. `docker compose up -d --build`: all services healthy; `docker compose config` shows no published DB port; gitleaks and `pip-audit` clean.
3. Fuzz the AI path with the fake provider: no 500s; "no, don't save" saves nothing; concurrent confirms create one row.
4. Key pool: run with 1 key, then 3 keys with fake 429s: requests fail over without sleeping; `/api/ai/health` shows per-key state, no secrets.
5. Live eval (manual, marked `live`): 40 EN/TA/Tanglish items on Groq; results recorded in `docs/ai.md`.
6. Playwright smoke through the real UI on desktop and a 375 px viewport; Lighthouse mobile run recorded.
7. Seeded demo: run the 9-minute script start to finish, including a deliberate Groq outage to show degraded mode.
8. AWS: push to main → Actions deploys → HTTPS URL loads on a phone; run the S3 → Lambda → SageMaker → score path; confirm the risk chip appears and QuickSight (or fallback) renders.
9. Docs check: every file under `docs/` matches the code; tracking files updated; both reports reference real screenshots and numbers.

## Open items needing Lebi

- New git repo name and visibility (private).
- Groq API key(s) at Phase 1; rotate the committed Postgres/pgAdmin passwords at Phase 0.
- AWS account, billing alarm and whether student credits exist; confirm the Cloud certification course name with Ms. Anusha.
- Exact deadlines (both IA3s) so the cut line can be fixed.
- Native-speaker scoring of the Tamil eval set (Lebi, ~1 h).

# 03 - Implementation Plan

Purpose: ordered, checkable phases to turn LivoCRM into the IA3 submission and the clinic follow-up demo without changing the stack.
Date: 2026-10-26 | Status: proposed, awaiting Lebi's go-ahead and the IA3 submission date `[?]` (not stated; ask) | Owner: Lebi (solo)
Stack is fixed: FastAPI, React/Vite, PostgreSQL, Redis, Nginx, Docker Compose, Alembic, shadcn/ui. LLM provider moves to Groq (details in `04-groq-migration.md`). Product scope (follow-up / no-show / missed-lead recovery for small Tamil Nadu clinics) comes from `docs/plan/08-feature-research.md`; Phase 2 below only lists the structural work the audit shows is needed.

## 0. Estimate summary

| Phase | Goal | Hours (low-high) | Gate |
|---|---|---|---|
| 0 | Stop-ship security + data integrity | 24-32 | no Critical/High left open from `02` |
| 1 | AI layer: provider interface + Groq + async + confirm flow | 22-30 | chat works on Groq with fallback, tests green |
| 2 | Domain pivot: workspace, roles, follow-up/no-show data model + API | 30-42 | demo scenario runs end to end |
| 3 | Frontend redesign + fixes + vitest | 26-36 | all pages on real API, no fake fallbacks |
| 4 | Test depth, CI, docs, IA3 report, demo kit | 18-26 | coverage targets in `05`, docs match code |
| 5 | Polish + buffer (perf, i18n Tamil strings, a11y, rehearsal) | 8-12 | rehearsed 5-minute demo |
| Total | | 128-178 h | roughly 4-5 weeks at 30-35 h/week |

If time is short, the **minimum viable IA3** is Phases 0, 1, the demo-critical parts of 2 (follow-up queue + no-show recovery), the redesign of 3 for 4 core screens, and the Phase 4 docs: about 85-100 h. Each phase lists what can be cut.

Conventions for every task: write the failing test first, small conventional commits (`fix:`, `feat:`, `refactor:`, `docs:`, `chore:`) on a branch `ia3/<phase>-<topic>`, update `STATUS.md`/`FIXES.md`, keep `docs/architecture.md`, `docs/docker.md`, `docs/API.md` in sync (docs-keeper agent), run everything in Docker (`docker compose run --rm backend pytest`).

---

## Phase 0 - Stop-ship security and data integrity (24-32 h)

Order matters: P0.0 first so every later fix lands with a test.

- [ ] **P0.0 Test harness (4 h).** `backend/tests/` with `conftest.py` (test Postgres in the compose `test` profile, per-test transaction rollback, httpx `AsyncClient` against the ASGI app, fake Redis, `FakeLLMProvider` stub), `pytest.ini`, `requirements-dev.txt`. Files: `backend/tests/conftest.py`, `backend/pytest.ini`, `backend/requirements-dev.txt`, `docker-compose.yml` (`test` profile). Accept: `docker compose run --rm backend pytest` runs and passes a smoke test hitting `/api/health`.
- [ ] **P0.1 Close published ports and rotate credentials - SEC-01 (2 h).** `docker-compose.yml` (remove `db.ports`, pgAdmin to `profiles: [dev]` bound to 127.0.0.1, pin tags), `.env.example`, `docs/pgadmin_setup.md`. Rotate DB + pgAdmin passwords in the real `.env` (Lebi action). Add gitleaks config + pre-commit. Accept: `docker compose config` shows no host port for `db`; gitleaks clean on HEAD. Test: script test in `05` section 7.
- [ ] **P0.2 Unblock the event loop and cap LLM time - SEC-02 (3 h, interim).** `chat.py:203` -> `await asyncio.to_thread(...)`; `bedrock_service.py` boto3 `Config(connect_timeout=3, read_timeout=15, retries=...)`; `asyncio.Semaphore(8)` around LLM calls. Superseded by Phase 1 but ships now. Accept: health endpoint stays under 100 ms during 5 slow chat requests. Test: `test_chat_does_not_block_loop`.
- [ ] **P0.3 Rate limiting and quotas - SEC-03 (5 h).** `backend/app/services/rate_limit.py` (Redis fixed window, dependency factory), apply to login/register/chat/insights; nginx `limit_req_zone`; uvicorn `--proxy-headers`; 429 with `Retry-After`. Files: `routers/auth.py`, `routers/chat.py`, `routers/ai.py`, `nginx/nginx.conf`, `backend/Dockerfile`. Accept: 6th login in a minute returns 429; counters expire. Tests: limiter unit tests + route tests.
- [ ] **P0.4 Fix confirmation logic - SEC-04 (3 h).** Negation-first parser now; real endpoint in Phase 1. File: `orchestrator.py:279-348`. Accept: table in `05` section 3 (20 utterances) passes. Test: parametrized `test_confirmation_parser`.
- [ ] **P0.5 Validate before write; fix failure path - SEC-05/06 (5 h).** Per-intent Pydantic models in `backend/app/schemas/ai_actions.py` (Literal stage/type, Decimal value, `extra="forbid"`); `_save_entity` uses `begin_nested()`, writes `ChatAction` only with legal values; Alembic `0008_chat_action_failed.py` adds `failed` to the CHECK; fix `activity_type` vs `type` mapping (CA-05); persist `tags`, `expected_close`, `source='ai_chat'`, `ai_session_id`; stop silently creating on "update not found". Accept: bad stage from the model yields a friendly message, 200 response, messages persisted, no 500. Tests: `test_save_entity_*` (bad stage, bad value, unknown key, not-found update).
- [ ] **P0.6 Release DB connection before LLM - SEC-07 (2 h).** Restructure `send_message` into: verify session -> commit/close -> provider call -> short persistence transaction. Accept: pool usage test with 40 concurrent fake-slow chats finishes. Test: `test_pool_not_held_during_llm`.
- [ ] **P0.7 Per-session lock + commit-before-publish - SEC-08/15 (3 h).** Redis lock helper in `session_manager.py`; publish events after commit. Accept: two simultaneous confirms create one entity. Test: `test_concurrent_confirm_single_entity`.
- [ ] **P0.8 FK ownership checks - SEC-09 (2 h).** `backend/app/services/ownership.py::require_owned(db, Model, id, user)`; use in `deals.py:74,93`, `activities.py:71`. Accept: attaching another user's contact returns 404. Test: cross-tenant matrix in `05` section 2.
- [ ] **P0.9 Input validation + error mapping - SEC-14 (3 h).** `Field` bounds, `Literal` enums (`StageUpdate`, `DealUpdate.status`, `ActivityCreate.type`), `Decimal` money, `EmailStr | ""`, handlers `IntegrityError`->409, `DataError`->422 in `main.py`; nginx `client_max_body_size 1m`. Accept: invalid enum returns 422 not 500. Tests: parametrized invalid payloads for every create/update route.
- [ ] **P0.10 Auth hygiene - SEC-12/22 (3 h).** Password 10-72 bytes, lower-cased unique email (migration `0009_lower_email_unique.py`), dummy hash on unknown user, `IntegrityError` -> generic 400/409, `sub` parse errors -> 401. Accept: tests in `05` section 1.
- [ ] **P0.11 JWT library and WS ticket - SEC-10/16 (4 h).** Replace python-jose with PyJWT (pin), add `iat/jti`; `POST /api/ws/ticket` one-time ticket in Redis; frontend `useWebSocket` uses ticket; chat WS checks session ownership (SEC-19); nginx log format without `$args`. Accept: WS connect with raw JWT rejected; ticket reuse rejected. Tests: WS tests with Starlette `TestClient.websocket_connect`.
- [ ] **P0.12 Logging without PII - SEC-13 (1 h).** Central logging config, remove raw-LLM logs at `data_extractor.py:99`, `intent_classifier.py:75`. Accept: caplog test asserts no phone/email in warning records.
- [ ] **P0.13 Container hygiene - SEC-17/18 (3 h).** `.dockerignore` (backend, frontend), non-root `USER`, healthchecks (backend `/api/health`, frontend, nginx), `depends_on: condition: service_healthy`, remove `env_file` from db, security headers + CSP at nginx. Accept: `docker compose ps` all healthy; `curl -I` shows headers.

Phase 0 exit criteria: all Critical/High findings closed, `pytest` green, gitleaks clean, `STATUS.md` + `FIXES.md` entries written.
Cut line: P0.11 (WS ticket) and P0.13 can slip to Phase 4 if the demo is not publicly hosted; everything else is non-negotiable.

---

## Phase 1 - AI layer: provider interface, Groq, async orchestrator, real confirm flow (22-30 h)

Full design in `04-groq-migration.md`. Tasks:

- [ ] **P1.1 Provider interface + fake provider (3 h).** `backend/app/services/llm/{base,factory,fake}.py`, `LLM_PROVIDER` setting. Bedrock wrapped as `bedrock_provider.py` unchanged in behaviour. Accept: engine runs on `fake` with no network; tests use it.
- [ ] **P1.2 Groq provider (5 h).** `groq_provider.py` on `httpx.AsyncClient`, JSON mode, timeouts, retries/backoff honouring `Retry-After`, usage accounting. Accept: contract tests against recorded fixtures.
- [ ] **P1.3 Guards (4 h).** Token/request budget per user (Redis), input char cap, output cap, circuit breaker, concurrency semaphore. Accept: over-budget returns a clear message and 429, never a crash.
- [ ] **P1.4 Async orchestrator + typed outputs (6 h).** `async def process_message`; Pydantic result models for intent/extraction; all prompts in `prompts.py` (fix CA-27 braces); delimiters for untrusted text; regex pre-extraction of phone/email. Accept: no sync LLM call remains (`grep boto3` only in the optional Bedrock adapter).
- [ ] **P1.5 Confirm/cancel endpoint (3 h).** `POST /api/chat/sessions/{id}/confirm` with pending-action id; frontend `ConfirmationCard` calls it; saving only happens there (fixes CA-09). Accept: text "yes" no longer writes data; button does.
- [ ] **P1.6 Insights + titles via provider (2 h).** `ai.py` and `session_naming.py` use the provider; `generated_by` hides model id (SEC-26).
- [ ] **P1.7 Cutover (3 h).** Default `LLM_PROVIDER=groq`, replay the utterance fixture set (EN/TA/Tanglish), compare to Bedrock baseline, then remove `bedrock_service.py`, `boto3`, AWS env vars; archive `docs/Bedrock_guide.md`. Accept: rollout checklist in 04 complete.

Exit: p95 chat turn under 3 s on Groq for the fixture set `[?]` (measure; do not promise before measuring), zero 500s in the AI fuzz tests.
Cut line: P1.3 circuit breaker and P1.7 baseline comparison can be simplified; interface + Groq + async are required.

---

## Phase 2 - Domain pivot: follow-up, no-show and missed-lead recovery (30-42 h)

The existing sales-pipeline CRM must become visibly a different product. Final entity list and screens come from `08-feature-research.md`; the audit shows these structural prerequisites:

- [ ] **P2.1 Workspace and roles (6-8 h).** New `workspaces`, `memberships(role: owner|staff|viewer)`; move `user_id` ownership to `workspace_id` (migration 0010+ with data backfill: one workspace per existing user); `require_role()` dependency; update all queries and the ownership helper. Accept: staff cannot delete, viewer cannot write; cross-workspace tests pass. (Without this the "receptionist + doctor" story is untestable.)
- [ ] **P2.2 Data model (8-10 h).** Proposal (confirm against 08): `appointments` (contact, starts_at, status: booked|attended|no_show|cancelled|rescheduled), `follow_up_tasks` (due_at, reason, channel, status, assigned_to), `message_templates` (EN/TA), `outbound_messages` (log with status, provider id, template, rendered text), `leads` stage `missed_call|enquiry|booked|lost` or reuse contacts+deals. Use `DateTime(timezone=True)`, `Decimal`, indexes on `(workspace_id, due_at, status)` and `(workspace_id, phone)`; phone normalised to E.164 (`+91...`). Alembic migrations dated 2026-10/11 so the history shows new work.
- [ ] **P2.3 Recovery engine (8-10 h).** Rules: appointment passed without `attended` -> no-show task; enquiry with no reply after N hours -> follow-up task; Redis-backed scheduler loop (APScheduler or a simple asyncio worker service in compose) with idempotent task generation. Accept: seed scenario produces the expected tasks exactly once. Tests: time-travel tests with an injectable clock.
- [ ] **P2.4 AI assist on Groq (4-6 h).** Draft follow-up message in EN/TA from template + context (structured JSON, human approves before send), classify inbound reply (confirm/reschedule/stop), summarise a patient history in one line. Never auto-send without approval. Untrusted-text delimiters (SEC-21).
- [ ] **P2.5 Messaging adapter (4-6 h).** `MessageChannel` interface with `LogOnlyChannel` (demo) and a stub for WhatsApp/SMS (provider chosen in 08). Webhook receiver with signature check `[?]`. Accept: demo works with no external account.
- [ ] **P2.6 API + OpenAPI hygiene (3-4 h).** Routers `appointments`, `follow_ups`, `templates`, `messages`, `recovery/summary`; response models everywhere; `docs/API.md` regenerated.
- [ ] **P2.7 Seed/demo data (2-3 h).** Script creating a clinic workspace, 3 users, 40 patients with Tamil/English names, appointments in the past/future, via an idempotent CLI (`python -m app.cli seed-demo`).

Exit: scenario "morning list: 6 no-shows, 4 overdue follow-ups, 3 missed enquiries -> approve drafts -> log sent -> dashboard shows recovered revenue" works from the UI.
Cut line: P2.5 real channel and P2.1 viewer role may be reduced to LogOnly + owner/staff.

---

## Phase 3 - Frontend redesign, fixes, vitest (26-36 h)

Design direction per Lebi's preferences: one strong visual direction (e.g. editorial/dark-minimal "recovery desk" ledger), no generic card grids, no blue-gradient hero. Shadcn/ui as customised base, Magic UI for motion, mobile-first (receptionist on a phone).

- [ ] **P3.1 Foundations (4 h).** Design tokens, fonts self-hosted (CA-28), INR formatting `Intl.NumberFormat('en-IN')` (CA-19), i18n scaffold EN/TA (strings table), Zod schemas for every API response, shared `useApi` error handling (toast), remove fake fallbacks (CA-16, CA-18).
- [ ] **P3.2 Core screens (12-16 h).** (a) Today queue (follow-ups + no-shows, approve/skip/snooze, keyboard-first), (b) Patient/lead detail timeline, (c) Message draft review drawer, (d) Recovery dashboard (recharts: recovered vs lost, response rate), (e) Chat assistant with real confirm card, (f) Settings with working profile + templates editor, (g) auth screens. Delete or reuse dead magicui components.
- [ ] **P3.3 State/WS fixes (3 h).** `useWebSocket` reconnect bug (CA-17), ticket auth, remove dead stream handlers, optimistic updates with rollback on Kanban/queue actions.
- [ ] **P3.4 Accessibility + responsive (3 h).** Focus states, aria on dialogs/queue, 360 px layouts, reduced motion.
- [ ] **P3.5 Frontend tests (6-8 h).** vitest + Testing Library + MSW; Playwright smoke (login -> approve a follow-up -> see log). See `05`.
- [ ] **P3.6 Cleanup (1 h).** Delete `frontend/tmp-scaffold/`, unused ui/magicui files, unused deps; run `tsc -b`, `eslint`.

Exit: `npm run build` clean under strict TS, zero `any`, all screens use the real API.
Cut line: Playwright and Tamil strings beyond core screens can shrink; the redesign of 4 core screens cannot.

---

## Phase 4 - Test depth, CI, documentation, IA3 report, demo kit (18-26 h)

- [ ] **P4.1 Reach coverage targets (6-8 h)** in `05` (auth 95%+, mutations 90%+ lines, overall backend 80%+).
- [ ] **P4.2 CI (2 h).** `.github/workflows/ci.yml`: ruff, mypy (strict on new code), pytest in compose, vitest, `tsc -b`, eslint, gitleaks, `pip-audit`, `npm audit`.
- [ ] **P4.3 Docs in sync (4-5 h).** Create `docs/architecture.md`, `docs/docker.md`, `docs/API.md` (docs-keeper agent); move `development_guide.md`, `walkthrough_problems.md`, `Bedrock_guide.md`, DBMS report to `docs/archive/`; refresh ER diagram.
- [ ] **P4.4 IA3 report (4-6 h).** Mapped to the six marking heads (below); real screenshots from the new UI; test and coverage report; security-review summary; reuse declaration (below).
- [ ] **P4.5 Demo kit (2-3 h).** `docker compose up` one-liner, seeded data, script with timings, fallback video, offline-safe (no CDN fonts), Groq-down fallback demonstrated deliberately.

## Phase 5 - Polish and buffer (8-12 h)
- [ ] Performance pass (indexes from CA-23 verified with `EXPLAIN`), load smoke (k6 or `hey`) on 5 endpoints.
- [ ] Remaining Low findings (SEC-23 to SEC-29), `/api/health` deep check, Redis shutdown.
- [ ] Two full rehearsals; fix whatever breaks; freeze.

---

## IA3 marking heads vs plan (30 marks)
| Head | Evidence to show | Plan item |
|---|---|---|
| Front-end design | New visual direction, responsive, Tamil/English, accessible | P3.1-P3.4 |
| Back-end integration | Typed API, Groq provider, Redis, scheduler, migrations, OpenAPI | P1, P2.2-P2.6 |
| Functionality | End-to-end recovery scenario, roles, confirm flow, failure fallbacks | P2, P1.5 |
| Presentation | Rehearsed demo, seeded data, offline fallback | P4.5, P5 |
| Innovation | AI-drafted bilingual follow-ups with human approval, no-show recovery engine, tanglish intent handling | P2.3-P2.4 |
| Documentation | Architecture, API, Docker docs, test and security reports, IA3 report | P4.3-P4.4 |

## Reuse-safety note (important)
The repo already produced a course submission: `docs/dbms_academic_report.{md,html,docx,pdf}` (Energy-sector B2B CRM, ER/normalization/SQLAlchemy chapters). For IA3 treat the codebase as a **declared base**, not as new work:

| Must be visibly new for IA3 | Where it shows |
|---|---|
| Different problem domain and users (clinic follow-up recovery, receptionist/owner roles) | Report intro, seed data, UI copy, no "energy/solar" strings anywhere |
| New data model + migrations 0008+ dated Oct-Nov 2026 | `alembic/versions/`, new ER diagram (not the old one) |
| New UI design and new screenshots taken for IA3 | `frontend/`, report figures |
| Groq-based AI layer replacing Bedrock, with tests and fallbacks | `app/services/llm/`, 04 |
| Test suite, CI, security review and fixes | `backend/tests`, `frontend/**/*.test.tsx`, `.github/workflows`, `docs/plan/02` |
| Git history showing incremental IA3 work | branches `ia3/*`, conventional commits, no single "big bang" commit |
| Written reuse declaration with a delta table (base vs new, by file/feature) | IA3 report appendix |

Also: do not paste text, tables or figures from the DBMS report; move its files to `docs/archive/` and cite it as prior work; check the college's rule on building on earlier submissions `[?]` and tell the evaluator up front.

## Risks
| Risk | Mitigation |
|---|---|
| Groq free-tier rate limits / model changes `[?]` | Budget guard, fallback to deterministic drafts, model names only via env (see 04, 08) |
| Scope creep in Phase 2 | Freeze the entity list after 08; cut channel integration first |
| Workspace migration touches every query | Do P2.1 before new features; tests from `05` section 2 guard it |
| Solo capacity | Fixed cut lines above; Phase 0 and 1 are the floor |

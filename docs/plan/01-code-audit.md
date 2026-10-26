# 01 - Code Audit

Purpose: as-built architecture, quality findings, doc-vs-code discrepancies and dead code for LivoCRM.
Date: 2026-10-26 | Status: complete (static analysis only; nothing was run, no containers started) | Auditor: code-audit agent
Legend: `[?]` = could not verify statically. Severity here is code quality/correctness; security ratings live in `02-security-review.md`.
Trust rule applied: where docs and code disagree, the code wins (section 4).

## 1. Architecture as-built

```
Browser --:3500--> nginx (nginx:1.27-alpine, nginx/nginx.conf)
   /ws/*  --> backend:8000 (WebSocket upgrade, 3600s timeouts)
   /api/* --> backend:8000 (120s timeouts)
   /*     --> frontend:80  (nginx:alpine serving Vite build, frontend/nginx.conf)
backend (python:3.12-slim, single uvicorn process, runs `alembic upgrade head` on every start)
   |-- PostgreSQL 16 (asyncpg, pool 10 + 20 overflow)
   |-- Redis 7 (AI session context only; no persistence; in-memory fallback)
   |-- AWS Bedrock Converse (boto3, sync)  <-- LLM provider today, NOT Groq
   |-- scikit-learn RandomForest (ml/model.pkl, trained at image build time on synthetic data)
pgAdmin 4 (:5050) and Postgres (:5435) are also published to the host.
```

| Layer | As-built facts |
|---|---|
| API surface | 35 HTTP routes + 2 WebSocket routes. Prefix `/api` (auth 3, contacts 5, deals 6, activities 4, pipeline-stages 5, analytics 3, ai 2, chat 6, health 1). WS: `/ws/dashboard/{user_id}`, `/ws/chat/{session_id}`. |
| Tenancy | One tenant = one `users` row. Every table has `user_id`; no organization/workspace, no roles (`users.plan` exists but is unused). All CRUD filters by `user_id == current_user.id`. |
| Auth | `POST /auth/register`, `/login` (JSON body, not OAuth2 form), `/me`. bcrypt (library direct), HS256 JWT via python-jose, 30 min, no refresh, no revocation. Token in `localStorage`. |
| Models (8 tables) | users, contacts, deals, activities, pipeline_stages, chat_sessions, chat_messages, chat_actions. Migrations 0001-0007 (indexes, CHECKs, unique, FK fix). |
| AI engine | `ai_engine/orchestrator.py` state machine IDLE -> COLLECTING -> CONFIRMING -> SAVING; 5 entity intents + QUERY_DATA (stub) + GENERAL_CHAT + MULTI_INTENT. Context in Redis (`livocrm:session:<uuid>`, TTL 3600 s, last 20 messages). |
| Realtime | In-memory `ConnectionManager` (single process only). Chat WS carries only `ai_typing`. Dashboard WS (`entity_created`, `dashboard_update`) is emitted by the backend but **no frontend code opens it**. |
| ML | RandomForest on 7 features; labels are generated from a hand-written linear formula (`ml/generate_data.py:22-36`), so the model re-learns a formula. `contacts.lead_score` is never written. |
| Frontend | React 19, Vite 8, TS strict, Tailwind 4, shadcn/ui (25 files in `components/ui`), Zustand 3 stores, axios, framer-motion, recharts. 8 pages: Dashboard, Contacts, Pipeline, Chat, Analytics, Settings, Login, Register. No tests, no zod, no react-query. |
| Infra | docker-compose: db, redis, backend, frontend, nginx, pgadmin. Healthchecks only on db and redis. No CI (`.github/` absent). No `.dockerignore`. |

### LLM call map (what the Groq migration replaces)
| Caller | File:line | Purpose | max_tokens / temp |
|---|---|---|---|
| `classify_intent` | `ai_engine/intent_classifier.py:46` | JSON intent, 1 call per IDLE message | 100 / 0.0 |
| `extract_data` | `ai_engine/data_extractor.py:66` | JSON field extraction | 500 / 0.0 |
| `generate_question` | `ai_engine/question_generator.py:61` | follow-up question | 150 / 0.7 |
| `_present_confirmation` | `ai_engine/orchestrator.py:253` | confirmation text | 300 / 0.3 |
| `_handle_general_chat` | `ai_engine/orchestrator.py:357` | persona chat, full history | 200 / 0.7 |
| `generate_session_title` | `services/session_naming.py:45` | background thread | 30 / 0.3 |
| `generate_bedrock_insights` | `services/bedrock_service.py:133` | dashboard insights (separate code path, no system prompt) | 220 / 0.2 |
Up to 3 sequential blocking LLM calls per user message (classify, extract, question/confirm), plus a 4th classify on long confirmations (`orchestrator.py:309`).

## 2. Findings

Severity: H = fix before any demo/deploy, M = fix in the main build, L = cleanup.

| ID | Sev | Area | Finding | Where | Fix (short) |
|---|---|---|---|---|---|
| CA-01 | H | async | Synchronous `Orchestrator.process_message` (boto3 blocking) called inside an `async def` handler; blocks the event loop for the whole LLM round-trip, freezing every other request and WebSocket. `IMPLEMENTATION_COMPLETE.md` claims event-loop blocking was eliminated; only Redis was made async. | `routers/chat.py:203`, `services/bedrock_service.py:96`, all `ai_engine/*` | Make orchestrator and provider `async`; interim `asyncio.to_thread`. See 04. |
| CA-02 | H | transactions | Request-scoped DB session (and its pooled connection) stays open across 3-4 LLM calls (no timeouts configured on boto3). 30 concurrent chats exhaust the pool. | `dependencies.py:18-20`, `chat.py:182-253` | Do LLM work before touching the DB, or commit and release before calling the provider. |
| CA-03 | H | error handling | Failure path of `_save_entity` writes `ChatAction.status="failed"` and `entity_type="unknown"`, both rejected by CHECK constraints from migration 0005. A failed flush also leaves the session in a rolled-back state, so the later `db.commit()` raises: request returns 500, chat messages are lost, Redis context is stuck in SAVING. | `chat.py:405,559,563-571`; `alembic/versions/0005:57-66` | Use `db.begin_nested()` per save; extend CHECK (`failed`) or map to `rejected`; validate payload first. |
| CA-04 | H | correctness | Confirmation precedence bug: affirmative words are checked before negatives, so "no, don't save it", "not ok", "change the email, ok?" all save. | `orchestrator.py:288-295` | Negation-first parsing, or explicit confirm/cancel endpoint (preferred). |
| CA-05 | M | correctness | `LOG_ACTIVITY` schema key is `activity_type` but the saver reads `type`, so every chat activity becomes `note`. `deal_title`, `expected_close`, contact `tags` are extracted but never persisted. Chat-created rows never set `source='ai_chat'` / `ai_session_id`. | `prompts.py:55`, `chat.py:411-421,465-471,532` | Align schema keys, persist all fields, set provenance. |
| CA-06 | M | correctness | LLM-provided values go to the DB without validation: `stage="won"`, `value="5k"`, unknown keys. Enum constraints exist only in Postgres, so bad values surface as swallowed exceptions (CA-03). | `data_extractor.py:85`, `chat.py:465-471,517-523` | Pydantic models per entity (Literal enums, Decimal), reject unknown keys. |
| CA-07 | M | correctness | "Update" intents locate records with `ilike('%name%') LIMIT 1` (no ordering), so "John" can update "Johnson"; if nothing matches, a new record is silently created instead. | `chat.py:433-440,498-505,451-461,517-526` | Resolve by exact/ID match, ask user to disambiguate. |
| CA-08 | M | correctness | `_looks_like_followup` matches generic words ("add", "also", "update", "and the", "@"), so almost any message after a save is treated as an update of the last saved entity. | `orchestrator.py:166-188` | Use the classifier result plus explicit reference resolution. |
| CA-09 | M | UX/contract | "Confirmation card" is cosmetic: it is built only when state is already SAVING (entity already saved in the same request) and its Confirm/Dismiss buttons only clear local state. | `chat.py:220-232,270-276`; `ChatPage.tsx:111-116` | Real two-step flow: `POST .../confirm` with `action`. |
| CA-10 | M | ordering | Events and cache are pushed before the commit: `push_entity_created` and `analytics_cache.invalidate` (separate session, cannot see uncommitted row) run at `chat.py:230-234`, commit at `:253`. Phantom events on rollback, stale stats. | `chat.py:228-253` | Commit first, then publish. |
| CA-11 | M | duplicated logic | `analytics_cache` sums pipeline value over all deal statuses; `routers/analytics.py:36` sums only `active`. Cache `get()` has no caller; only `invalidate()` is used, and the dashboard WS has no frontend consumer. Whole realtime-dashboard chain is dead. | `services/analytics_cache.py:69-82`, `routers/websocket.py:125-164`, `routers/chat.py:233` | Delete or wire up (single stats function). |
| CA-12 | M | ML | `days_since_last_activity` is never supplied (always 30), `lead_score` never persisted, scoring runs sync CPU + pandas inside an async route, labels are synthetic from a formula. Weak story for a "ML" claim; keep for the demo only if described honestly. | `routers/ai.py:36-48`, `lead_scoring.py:28-39`, `ml/generate_data.py` | Compute recency, persist score, or replace by rules + LLM rationale. |
| CA-13 | M | session store | `reset_context` rebuilds from `_context_store` (process memory) not Redis, so after restart/other worker the history is lost; `_context_store` is never evicted (memory leak); no lock around read-modify-write per session. | `session_manager.py:45,112,142-147`, `chat.py:202-207` | Redis only (+ per-session lock), drop memory fallback or add TTL/LRU. |
| CA-14 | M | transactions | `register` commits the user, then `seed_default_pipeline_stages` commits again; failure between leaves a user with no stages. Check-then-insert on email races to an unhandled `IntegrityError` (500). | `routers/auth.py:18-32` | Single transaction, catch `IntegrityError` -> 409. |
| CA-15 | M | design | `pipeline_stages` CRUD exists but the frontend never calls it (stages are hard-coded) and `deals.stage` has a CHECK on six fixed values, so custom stages cannot work. Router + table are dead weight or a design contradiction. | `routers/pipeline_stages.py`, `models/deal.py:58-61`, `PipelinePage.tsx` | Decide: fixed enum (delete router) or stage FK. |
| CA-16 | M | frontend errors | Silent failure: `ContactsPage.handleSave` swallows errors ("demo mode"), `handleDelete` fakes success locally; Dashboard catch shows zeros; `getAISummary` falls back to a hard-coded "Sarah Johnson" paragraph and the endpoint returns generic insights, not per-contact; `PipelinePage` uses `alert()`. | `ContactsPage.tsx:137-149,184-191`, `DashboardPage.tsx:136-142`, `PipelinePage.tsx:120` | Toast real errors; remove fake fallbacks. |
| CA-17 | M | frontend WS | `useWebSocket` reconnects after unmount/session switch (cleanup closes the socket, `onclose` then schedules a new timer after the timer was cleared); `connect` identity changes with `onMessage`, causing reconnect churn. Handles `ai_chunk/ai_message/ai_stream_start` events the backend never sends. | `hooks/useWebSocket.ts:50-60,73-80`, `hooks/useChat.ts:39-62` | Guard with a `closedByUs` ref; remove dead handlers. |
| CA-18 | M | frontend logic | Offline "local session" fallback creates `local-<ts>` ids; sending then POSTs to `/chat/sessions/local-.../message` (422). `sendMessage` posts to `/chat/sessions//message` when no active session. | `hooks/useChat.ts:109-121,146-149` | Remove fallback, disable input without a session. |
| CA-19 | M | frontend | Settings page is static (hard-coded "Lebi Raja / lebi@livocrm.com / America/New_York"), "Save" only flashes a flag; theme default dark vs docs. Currency is hard-coded `$` (`formatCurrency`) - wrong for an India demo (INR, lakh/crore). | `SettingsPage.tsx:35-57`, `DashboardPage.tsx:107`, `PipelinePage.tsx:39` (duplicated helper) | Real profile endpoint or remove; `Intl.NumberFormat('en-IN')`. |
| CA-20 | M | frontend typing | `VITE_WS_URL` read but not declared in `vite-env.d.ts`; no Zod at API boundary (convention); `DealCreate.contact_id` is a free-text UUID input; type `source` exists on frontend types but `ContactRead`/`DealRead` do not return `source` (so `SourceBadge` cannot work). | `hooks/useWebSocket.ts:5`, `types/index.ts:26,61`, `schemas/contact.py:27-40` | Add Zod parsing; add `source` to read schemas; contact picker. |
| CA-21 | M | Pydantic gaps | Request schemas have unbounded `str`, free-text `stage/status/type`, `email: str` (not `EmailStr`), money as `float` over a `Numeric(12,2)` column, `StageUpdate.stage: str`. Return types are un-annotated for analytics/ai (`dict`). | `schemas/*.py`, `deals.py:19-20`, `analytics.py`, `ai.py` | Literal enums, `Field` bounds, `Decimal`, response models. |
| CA-22 | M | N+1 / queries | `ai/insights` issues 5 sequential COUNT queries; `analytics/summary` 3; list endpoints run COUNT + SELECT (fine). `get_session` loads all messages unpaginated. No N+1 found in ORM loops (no relationship lazy-loads in handlers). | `routers/ai.py:58-80`, `chat.py:123-128` | Single aggregate query; paginate messages. |
| CA-23 | M | indexes | Missing: `contacts(user_id, phone)` / `(user_id, email)` lookups (critical for the clinic use case: match by phone), trigram index for `ilike '%q%'` search, `activities(user_id, occurred_at)`, `chat_messages(session_id, created_at)`, `deals(user_id, stage)`. | models + migrations 0004 | New migration. |
| CA-24 | L | time handling | `datetime.utcnow()` (naive, deprecated 3.12) used for `timestamptz` columns and `onupdate`; mixture of aware/naive. asyncpg treats naive values as local time [?] (container TZ is UTC so unobserved). | `chat.py:251,317,369,534`, `models/*.py` `onupdate` | `datetime.now(timezone.utc)` or server-side `now()`. |
| CA-25 | L | tasks | `asyncio.create_task(...)` result not retained (task may be GC'd); title race: check `title == "New Chat"` before commit. | `chat.py:248,259` | Keep a set of tasks or use a background-tasks queue. |
| CA-26 | L | logging | No `logging.basicConfig`; `logger.info` lines (model loaded, auto-named) never appear at default WARNING level. `logger` defined before imports in `main.py`. | `main.py:10-12` | Central logging config (JSON, request id). |
| CA-27 | L | prompts | `DATA_EXTRACTOR_SYSTEM` uses `{{ }}` but is never `.format`-ed, so the model sees literal double braces. Prompts are spread over `bedrock_service.py:117`, `session_naming.py:19`, `orchestrator.py:247`, `data_extractor.py:632`, `question_generator.py:731` in addition to `prompts.py`. Activity enum in prompt lacks `task` (DB allows it). | `prompts.py:74-82` | Move all prompt text to `prompts.py`; fix braces. |
| CA-28 | L | deps | `python-dotenv` unused (pydantic-settings reads `.env`); `redis>=5.0.0`, `boto3>=1.34.0` unpinned (violates pin convention); `numpy`, `pandas` heavy for one-row inference; frontend `date-fns`, `geist`, `@fontsource-variable/inter` unused, `shadcn` CLI listed as runtime dependency; fonts loaded from jsdelivr CDN (`index.css:9,16`) so an offline demo loses fonts. | `requirements.txt`, `package.json`, `index.css` | Prune; self-host fonts. |
| CA-29 | L | config | `SECRET_KEY` check is length-only (`config.py:33`), contrary to `IMPLEMENTATION_COMPLETE.md` ("fails if placeholder"). Two divergent `.env.example` files (root has AWS vars, `backend/.env.example` lacks DB/Redis creds, neither lists `BEDROCK_ENABLED/MAX_TOKENS/TEMPERATURE`); `VITE_API_URL` is not consumed by compose build. | `config.py`, `.env.example`, `backend/.env.example` | One `.env.example`; reject known placeholders. |
| CA-30 | L | nginx | `proxy_set_header Host $host` drops the port, so FastAPI trailing-slash redirects point to `http://localhost/...` (port 80); `Connection "upgrade"` is sent on every `/` request. | `nginx/nginx.conf` (`/api/`, `/` blocks) | `$http_host`; use the `$connection_upgrade` map or drop it for `/`. |
| CA-31 | L | misc | `.gitignore` has `ml/*.pkl` (anchored to repo root, not `backend/ml/`); `/api/health` does not check DB/Redis; Swagger `/docs` open; `main.py` lifespan has empty shutdown (Redis client never closed). | `.gitignore`, `main.py:25-30,76-78` | Fix patterns, deep health check, close clients. |

### Tests, CI, tooling
- **Tests: none.** No `tests/` directory in backend; no vitest/jest config or test script in `frontend/package.json`; no Playwright. Confirmed by `find` (no `test*` files outside `node_modules`). `CODEBASE_ANALYSIS.md:155,345` says the same.
- **CI: none** (`.github/` absent). No lint/type-check gate (ESLint config exists; no ruff/mypy for Python).
- Not run: `tsc -b`, `eslint`, `ruff`, `mypy`, `pip-audit`, `npm audit` (no `node_modules`, no venv; skipped per instructions) `[?]`. Static grep found zero `any` in `frontend/src` outside generated `components/ui`; strict mode is on (`tsconfig.app.json:98`).

### Docker / env hygiene
| Item | State |
|---|---|
| `env_file` | Used for db and backend (good) but db receives the entire `.env` (AWS keys, SECRET_KEY): `docker-compose.yml:5`. |
| Healthchecks | db, redis only. Missing: backend, frontend, nginx (convention violated). nginx `depends_on` has no `condition: service_healthy`. |
| Restart policy | redis, nginx, pgadmin have it; backend/frontend/db do not. |
| Images | `pgadmin4:latest`, `nginx:alpine` unpinned; python/node pinned to major. |
| Users | All app containers run as root. |
| `.dockerignore` | Absent in backend and frontend: `COPY . .` bakes any local `.env`, `node_modules`, `tmp-scaffold` into images. |
| Ports | Published: 3500 (ok), 5435 -> Postgres, 5050 -> pgAdmin (see security review SEC-01). |
| Migrations | Run in `CMD` on every start (unsafe with >1 replica). ML training at image build (`Dockerfile:14`) slows builds but removes the "model missing" problem described in `walkthrough_problems.md`. |
| Redis | `--save "" --appendonly no`, no password, no maxmemory (fine on private network). |

## 3. Redis and WebSocket lifecycle
| Concern | Detail |
|---|---|
| Redis init | Lazy, first `get_context`; if Redis down at that moment, `_redis=None` so every call retries a ping (latency). Never re-checked after a mid-run failure; stale in-memory copies diverge. |
| Redis shutdown | Client never closed (`main.py:30`). |
| WS manager | Single-process dict; breaks with >1 uvicorn worker or replica. `disconnect_*` only on `WebSocketDisconnect`; other exceptions leak entries (`websocket.py:163,199`); dead sockets are dropped from sets but empty keys are not deleted (`:56,:78`). |
| WS auth | Token checked once at connect (expiry not enforced afterwards); chat WS does not check session ownership (`websocket.py:189-191`). |
| WS client | Reconnect bug CA-17; token in query string. |
| Keepalive | Server only answers literal `"ping"`; no server-side ping/idle timeout besides nginx 3600 s. |

## 4. Documentation vs code discrepancies
| Doc | Claim | Reality (code) |
|---|---|---|
| `docs/ARCHITECTURE_OVERVIEW.md:3-20,57-68` | Stack is FastAPI+React+Postgres only; "frontend auth client calls `/users/*`", "IDs are numeric", "list endpoints return raw arrays", "no `/analytics` route", insights are placeholder text | Redis, nginx, chat/WS and the AI engine exist; auth client calls `/auth/*` (`api/auth.ts`); IDs are UUID strings; lists return `PaginatedResponse{total,items}`; `/analytics` is routed (`App.tsx:72`); insights call Bedrock with deterministic fallback (`bedrock_service.py:178`). |
| `docs/BACKEND_DOCUMENTATION.md:8,25-31,95-99` | Uses passlib; CORS lacks `:3500`; Redis and AWS "declared, not used"; pipeline-stage router not implemented; no pagination envelope | bcrypt used directly (`auth_service.py:5`); `:3500` is allowed (`main.py:45`); Redis (`session_manager.py`) and Bedrock are live; `pipeline_stages.py` exists (113 lines); envelope exists. Chat and WS routes are undocumented. |
| `docs/DATABASE_SCHEMA_AND_ERD.md` | 5 tables, 0001 is "source of truth", `activities.contact_id` CASCADE, hardening "future" | 8 tables; migrations 0002-0007 add chat tables, `source`/`ai_session_id`, 10 CHECKs, indexes, unique `(user_id,name)`; activities FK is now `SET NULL` (0007). ERD omits `chat_*`. |
| `docs/FRONTEND_DOCUMENTATION.md:43-48,74,98-130` | Login/Register "not routed"; routes limited to 4; stores `refresh_token`; API base `http://localhost:8000/api`; pages fall back to mock data; contract gaps (numeric ids, array lists, `/pipeline/stages/*`) | Login/Register/Chat/Analytics are routed; only `access_token` stored; base is `/api`; those mismatches are resolved (mock fallbacks mostly removed, see CA-16). |
| `docs/development_guide.md` (whole file) | Next.js App Router BFF, Neo4j, MinIO, Google OAuth, resume parser, `backend_api.py` | **Describes a different project.** Nothing in this repo matches. Delete or archive. |
| `docs/walkthrough_problems.md` | Auth broken (passlib/bcrypt), Bedrock "not wired", ML model missing, CORS missing `:3500` | All resolved or inaccurate now; paths refer to `/home/lebi/projects/livocrm`. Historical only. |
| `CODEBASE_ANALYSIS.md` | 18 issues, e.g. "no request validation", "WebSocket lifecycle", "no RBAC", "no rate limiting", "no tests" | Still true: RBAC, rate limiting, tests, WS lifecycle, FK-ownership validation. Fixed since: Redis async, indexes, CHECKs. |
| `IMPLEMENTATION_COMPLETE.md` | "Event loop blocking eliminated"; "SECRET_KEY fails if placeholder"; "Users see confirmation card before AI creates entities; can approve/dismiss"; "Remove mock data"; "WebSocket authenticated" | LLM calls still block the loop (CA-01); only length checked (CA-29); card appears after the save and does nothing (CA-09); fake summary remains (CA-16); WS auth is token-validity only, chat WS lacks ownership (SEC-19). |
| `docs/dbms_academic_report.*` | Energy-sector B2B CRM, "AI CRM chat console", screenshots "simulation" | Prior course submission; see reuse note in `03-implementation-plan.md`. Not audited line by line. |
| Not audited in detail `[?]` | `LivoCRM_Plan.md`, `ai-driven_plan*.md`, `implementation_plan_v1/v2_migration.md`, `Bedrock_guide.md`, `README_CODEBASE_DOCUMENTATION.md`, `er_diagram*.html` | Planning/history docs; treat as stale until Bedrock removal. `docs/pgadmin_setup.md:42` embeds a DB password (see security review). |

## 5. Dead code and deletion candidates
| Path | Why |
|---|---|
| `frontend/tmp-scaffold/` (19 tracked files, 240 KB) | Vite scaffold leftover, not imported, own `package.json`. Delete. |
| `frontend/src/assets/react.svg`, `vite.svg`, `src/App.css` | Scaffold leftovers; no references in `src/` or `index.html` (grep). |
| `frontend/src/components/magicui/{SourceBadge,LiveIndicator,NumberTicker,AiTypingDots}.tsx` | Not imported anywhere (grep). Use them in the redesign or delete. |
| `frontend/src/components/ui/{calendar,dropdown-menu,popover,progress,scroll-area,select,sidebar,table,tabs}.tsx` | No importer outside `ui/` `[?]` (relative-import cases not exhaustively checked). |
| `frontend/src/api/analytics.ts:37-42` | "Legacy aliases" with no callers (grep). |
| `hooks/useChat.ts` streaming handlers (`ai_chunk`, `ai_message`, `ai_stream_start`), unused `send/wsStatus` deps | Backend never emits these. |
| `backend/app/services/analytics_cache.py` + `push_dashboard_update` / `push_entity_created` / `/ws/dashboard` | No consumer (CA-11). |
| `backend/app/routers/pipeline_stages.py`, `seed_service.py`, `schemas/pipeline.py` | Unused by UI (CA-15). |
| `python-dotenv`, `date-fns`, `geist`, `@fontsource-variable/inter` | Unused dependencies. |
| `docs/development_guide.md`, `docs/walkthrough_problems.md`, `docs/Bedrock_guide.md` (after cutover) | Wrong/stale; move to `docs/archive/`. |
| `Intent.QUERY_DATA` handler (`orchestrator.py:376-398`) | Returns "coming soon"; implement (read-only NL query is a good demo feature) or remove. |

## 6. What is good (keep)
- Consistent user scoping on every CRUD route (`user_id` in every WHERE); no SQL string building (all SQLAlchemy Core/ORM parameters); no mass-assignment (schemas whitelist fields).
- Async SQLAlchemy 2.0 typed models (`Mapped[...]`), UUID PKs, CHECK constraints, FK delete rules thought through.
- Deterministic fallbacks on every LLM call (the system degrades instead of crashing) - preserve this behaviour in the Groq provider.
- Clean Pydantic v2 schemas with `from_attributes`, paginated envelope, global 500 handler that hides stack traces.
- TypeScript strict, zero `any`, small typed API modules, error boundary.

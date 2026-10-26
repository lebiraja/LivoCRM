# FIXES

Real bug fixes only. Newest on top. Each entry: symptom, root cause, fix with `file:line`, verification.

_Findings come from `docs/plan/01-code-audit.md` and `docs/plan/02-security-review.md`; each one that gets fixed is logged below the template._

## Entry template
```
## YYYY-MM-DD · <short title>
- **Symptom:** what the user or test saw
- **Root cause:** why it happened
- **Fix:** what changed, `path/file.py:line`
- **Verification:** test name or command and result
- **Finding ref:** ID from docs/plan/
```

## 2026-10-26 · Extractor system prompt showed the model literal double braces
- **Symptom:** the model was told to answer `{{"extracted": {{...}}}}`, an invalid JSON example.
- **Root cause:** `DATA_EXTRACTOR_SYSTEM` was written as if `.format()`-ed but never is.
- **Fix:** single braces (`backend/app/services/ai_engine/prompts.py:78`).
- **Verification:** `tests/test_quick_wins.py::test_extractor_prompt_has_single_braces`.
- **Finding ref:** CA-27

## 2026-10-26 · Lead score ignored activity recency
- **Symptom:** every contact was scored as if its last activity was 30 days ago.
- **Root cause:** `/api/ai/score/{id}` never passed `days_since_last_activity`, so feature engineering used its default; the activity count was also not filtered by owner.
- **Fix:** one query for count and `max(occurred_at)` scoped to the user; recency in whole days passed to the model when any activity exists (`backend/app/routers/ai.py:37-52`).
- **Verification:** `tests/test_quick_wins.py::test_lead_score_uses_days_since_last_activity` (activities 40 and 10 days ago -> count 2, recency 10).
- **Finding ref:** CA-12

## 2026-10-26 · LIKE wildcards in contact search were not escaped
- **Symptom:** searching `%` or `_` matched every contact.
- **Root cause:** `ilike(f"%{search}%")` passed user text as a pattern.
- **Fix:** `Contact.name.icontains(search, autoescape=True)` (`backend/app/routers/contacts.py:29,34`). The chat lookups that used `ilike` were replaced by exact matches in the SEC-05 fix.
- **Verification:** `tests/test_hardening.py::test_contact_search_escapes_wildcards[%|_|clinic]`.
- **Finding ref:** SEC-25

## 2026-10-26 · OpenAPI docs open by default; insights leaked the internal model id
- **Symptom:** Swagger and `openapi.json` were served to anyone; `/api/ai/insights` returned `generated_by: "bedrock:<model id>"`.
- **Root cause:** FastAPI defaults; `get_insights` built the label from `BEDROCK_LLM_MODEL`.
- **Fix:** docs and schema only when `ENABLE_DOCS=true`, at `/api/docs` and `/api/openapi.json` (`backend/app/main.py:43`, `config.py:24`); `generated_by` is `"ai"` or `"fallback"` (`backend/app/services/bedrock_service.py:189,192`).
- **Verification:** `test_api_docs_disabled_by_default[5 paths]`, `test_generated_by_hides_model_id`; live stack: `/api/docs` and `/api/openapi.json` 404.
- **Finding ref:** SEC-26

## 2026-10-26 · Redis without a password or memory cap
- **Symptom:** any container on the network could read chat context, locks and tickets; memory unbounded.
- **Root cause:** `redis-server` started with no `requirepass`/`maxmemory`.
- **Fix:** `--requirepass "$REDIS_PASSWORD" --maxmemory "$REDIS_MAXMEMORY" --maxmemory-policy allkeys-lru`, healthcheck authenticates via `REDISCLI_AUTH` (`docker-compose.yml:26-38`); `REDIS_URL` carries the password (`.env.example:10-13`).
- **Verification:** live stack: unauthenticated `redis-cli ping` -> `NOAUTH Authentication required`; `maxmemory-policy allkeys-lru`; backend healthy and rate limits working through Redis.
- **Finding ref:** SEC-28

## 2026-10-26 · CORS origins hard-coded, all methods and headers allowed
- **Symptom:** origins fixed to localhost in code; `allow_methods=["*"]`, `allow_headers=["*"]`.
- **Root cause:** dev defaults in `main.py`.
- **Fix:** `CORS_ORIGINS` (comma-separated) from env (`backend/app/config.py:22,37`); methods limited to GET/POST/PATCH/DELETE/OPTIONS and headers to Authorization/Content-Type (`backend/app/main.py:51-54`).
- **Verification:** `test_cors_origins_from_env`, `test_cors_preflight[allowed|evil origin]`.
- **Finding ref:** SEC-23

## 2026-10-26 · Edge hardening: no CSP or security headers, server version exposed
- **Symptom:** API and WS responses carried no security headers; frontend asset responses lost theirs; nginx advertised its version; no TLS-independent clickjacking protection on `/api`.
- **Root cause:** headers only in the frontend container's config (and dropped in its asset `location`); `server_tokens` on.
- **Fix:** at the edge: `server_tokens off`, CSP (`default-src 'self'`, `img-src 'self' data:`, `font-src 'self'`, `frame-ancestors 'none'`, styles allow inline for UI libraries), `X-Content-Type-Options`, `X-Frame-Options DENY`, `Referrer-Policy`, `Permissions-Policy`, all `always` (`nginx/nginx.conf:16,53-58`); frontend copies hidden to avoid duplicates (`:130`); `/healthz` for the container check; edge 429s answer JSON with `Retry-After: 60`. Body limit 1m was SEC-14. HSTS waits for TLS (Phase 6).
- **Verification:** live stack: `curl -I http://localhost:3500/` shows all five headers and `Server: nginx` without version; 120 parallel `/api/health` calls -> 77 x 429 with `Retry-After: 60`.
- **Finding ref:** SEC-18

## 2026-10-26 · Containers ran as root, could bake local .env, and had no readiness gating
- **Symptom:** backend ran as root; `COPY . .` with no `.dockerignore`; `db` received the whole `.env` (SECRET_KEY, AWS keys); only db/redis had healthchecks and nginx started before its upstreams were ready.
- **Root cause:** default Dockerfile and compose wiring.
- **Fix:** `backend/.dockerignore` (env files, caches, generated model data); runtime image runs as uid 10001 with code and `ml/model.pkl` root-owned and read-only to it (`backend/Dockerfile:9,39`, also SEC-24); `db` has no `env_file` (`docker-compose.yml:6`); healthchecks on backend (`/api/health`), frontend, nginx (`/healthz`) and authenticated redis; backend waits for healthy db/redis, nginx for healthy frontend/backend; `restart: unless-stopped` on backend/frontend. `scripts/check_compose_policy.py` now also fails on a missing healthcheck or a db `env_file`.
- **Verification:** `docker compose up -d --build`: all five services `(healthy)`; backend `id` -> `uid=10001(app)`; `/app/.env` absent in the image; `db` env has no `SECRET_KEY`; policy script ok.
- **Finding ref:** SEC-17, SEC-24

## 2026-10-26 · PII and raw model output in logs
- **Symptom:** the extractor logged the full raw LLM reply (names, phones, emails), the classifier logged `raw[:200]`, titles derived from user text were logged, SQL errors embed row values, and uvicorn printed full query strings (a WS `?token=` JWT or a contact search term).
- **Root cause:** debug-style logging, no logging config (CA-26) and no redaction.
- **Fix:** log type names and lengths only (`services/ai_engine/data_extractor.py`, `intent_classifier.py`, `session_naming.py`, `bedrock_service.py`, `routers/chat.py` title log); `backend/app/logging_config.py` installs one root handler whose formatter masks emails, phone numbers and every URL query string, and routes uvicorn's loggers through it (called in `main.py:26`); engine `hide_parameters=True` (`backend/app/database.py:17`).
- **Verification:** `test_no_pii_in_logs` (caplog), `test_redacting_formatter_masks_email_and_phone`, `test_query_strings_redacted[3]`, `test_uvicorn_logs_use_redacting_handler`; live stack: 0 backend log lines with a ticket/token value after WS connects with `?ticket=` and `?token=`.
- **Finding ref:** SEC-13, CA-26

## 2026-10-26 · Chat context kept in an unbounded per-process dict and not bound to its owner
- **Symptom:** after a restart (or on another worker) `reset_context` rebuilt history from process memory and lost it; the in-memory dict grew forever; Redis keys `livocrm:session:<session>` carried no user binding.
- **Root cause:** dual store (Redis plus `_context_store` fallback) with reads preferring the process copy.
- **Fix:** Redis is the only store, key `livocrm:ctx:<user>:<session>` with a 1 h TTL; on Redis errors a turn starts fresh and logs a warning (`backend/app/services/session_manager.py:30,61`); `reset_context` builds from the live context; callers pass the user id (`routers/chat.py`).
- **Verification:** `tests/test_session_context.py` (`test_context_survives_process_restart`, `test_context_bound_to_user`, `test_redis_down_gives_fresh_context`).
- **Finding ref:** SEC-20, CA-13

## 2026-10-26 · WebSocket lifecycle: any user could subscribe to any chat session, leaks on errors, no cap
- **Symptom:** the chat WS checked only token validity, so any logged-in user could listen to another user's session; sockets were removed from the manager only on `WebSocketDisconnect`, so other errors leaked entries; no per-user connection limit.
- **Root cause:** ownership check skipped "to avoid a DB query"; narrow `except`; no counting.
- **Fix:** chat tickets are issued only for the caller's own session and bound to its id (`backend/app/routers/websocket.py:177`); per-user cap of 5 sockets, close code 4029 (`websocket.py:33`); loops catch every exception and always release in `finally` (`websocket.py:219-229`).
- **Verification:** `tests/test_ws.py::test_chat_ticket_requires_owned_session`, `test_chat_ticket_bound_to_session`, `test_connection_cap_per_user`, `test_error_in_loop_cleans_up`.
- **Finding ref:** SEC-19

## 2026-10-26 · JWT carried in WebSocket URLs and written to access logs
- **Symptom:** `?token=<jwt>` on `/ws/*` appeared in nginx's default combined log; a leaked line allowed replay for the token's lifetime.
- **Root cause:** browsers cannot send headers on the WS handshake, so the JWT was put in the query string; nginx logged `$request` with args.
- **Fix:** `POST /api/ws/ticket` (`{"channel":"dashboard"}` or `{"channel":"chat","session_id":...}` -> `{"ticket","expires_in":30}`) issues a single-use Redis ticket bound to user, channel and session (`backend/app/services/ws_tickets.py`, `routers/websocket.py:177`); both WS endpoints admit only `?ticket=`, redeemed with `GETDEL` (`websocket.py:200`), close codes 4001 missing, 4002 invalid/used/expired, 4003 wrong user/session/channel; nginx `log_format noargs` uses `$uri` (`nginx/nginx.conf:12`).
- **Verification:** `tests/test_ws.py::test_ticket_admits_once`, `test_raw_jwt_rejected`, `test_dashboard_ticket_bound_to_user`, `test_dashboard_ticket_contract`, `test_ticket_request_validated`, `test_ticket_requires_auth`; `nginx -t` ok.
- **Finding ref:** SEC-10

## 2026-10-26 · python-jose (algorithm-confusion and JWE DoS advisories) and unpinned dependencies
- **Symptom:** `python-jose[cryptography]==3.3.0` is below the fixed release for CVE-2024-33663/33664; `redis>=5.0.0` and `boto3>=1.34.0` resolved to whatever was newest at build time; tokens had no `iat`/`jti`.
- **Root cause:** library choice and loose pins.
- **Fix:** `PyJWT==2.15.1`, decoding requires `exp` and `iat`, tokens get `iat` and a random `jti` (`backend/app/services/auth_service.py:31,40`); `redis==8.1.0`, `boto3==1.43.118` pinned to the versions the suite runs on (`backend/requirements.txt`). Still open: `pip-audit` reports Starlette 0.38.6 advisories (needs a FastAPI upgrade) and python-dotenv 1.0.0 (unused, removed in 0.9); token storage in localStorage (SEC-11) is a frontend/Phase-1 item.
- **Verification:** `tests/test_tokens.py` (`test_token_has_iat_and_unique_jti`, `test_bad_token_is_401[expired|tampered|alg_none|wrong_key|no_iat]`); full suite 118 passed.
- **Finding ref:** SEC-16, SEC-11 (iat/jti part)

## 2026-10-26 · Token with a non-UUID `sub` caused a 500
- **Symptom:** a validly signed token whose `sub` was not a UUID (or empty) made every authenticated route return 500.
- **Root cause:** `UUID(user_id)` in `get_current_user` raised `ValueError` outside any handler.
- **Fix:** parse `sub` inside `try/except ValueError` and answer 401 (`backend/app/dependencies.py:35`).
- **Verification:** `tests/test_validation.py::test_bad_sub_is_401` (non-UUID, empty, missing, unknown user).
- **Finding ref:** SEC-22

## 2026-10-26 · Invalid input reached the database and came back as 500s
- **Symptom:** `stage="won"`, `status="open"`, `type="sms"`, a 256-char name, negative or 3-decimal money, `null` for NOT NULL fields, a duplicate pipeline-stage name or an int32-overflowing position all produced 500s; nginx accepted 20 MB bodies.
- **Root cause:** request schemas used free-text `str`, unbounded strings and lists, `float` money and `str` email; no handler for `IntegrityError`/`DataError`.
- **Fix:** bounded, typed schemas: `Literal` stage/status/type, `Decimal` money matching `Numeric(12,2)`, `EmailStr | ""`, length and list caps, explicit `null` rejected on NOT NULL update fields (`backend/app/schemas/contact.py`, `deal.py`, `activity.py`, `pipeline.py`; `StageUpdate` in `routers/deals.py`); contact search capped at 100 chars; `IntegrityError` -> 409 and `DataError` -> 422 with generic bodies (`backend/app/main.py:56,63`); `client_max_body_size 1m` (`nginx/nginx.conf:13`). `DealRead.value` stays a JSON number for the frontend.
- **Verification:** `test_invalid_payloads_return_422[15 cases]`, `test_invalid_deal_update_returns_422[5]`, `test_invalid_stage_move_returns_422`, `test_invalid_contact_update_returns_422[3]`, `test_duplicate_stage_name_is_409`, `test_db_error_handlers`; `nginx -t` ok.
- **Finding ref:** SEC-14, CA-21

## 2026-10-26 · Records could reference another tenant's contact or deal
- **Symptom:** user B could create or update a deal, or log an activity, pointing at user A's contact or deal UUID.
- **Root cause:** `contact_id`/`deal_id` from the body went straight into the row; only the FK existence was checked by Postgres.
- **Fix:** `require_owned()` returns 404 unless the referenced row belongs to the caller (`backend/app/services/ownership.py`), used in `routers/deals.py:77,97` and `routers/activities.py:75,77`.
- **Verification:** `tests/test_tenancy.py::test_cross_tenant_fk_reference_rejected[4 cases]` failed before (2xx), 404 after; `test_own_fk_reference_allowed` still 201.
- **Finding ref:** SEC-09

## 2026-10-26 · Chat events published before the entity was committed
- **Symptom:** dashboard listeners got `entity_created` for rows that could still roll back, and the analytics recompute (separate session) could not see the new row.
- **Root cause:** `push_entity_created` and `analytics_cache.invalidate` ran before `db.commit()` in `send_message`.
- **Fix:** commit first, then write the Redis context, then publish (`backend/app/routers/chat.py:290`).
- **Verification:** `tests/test_save_entity.py::test_event_published_after_commit` checks from a second connection that the contact exists when the event fires.
- **Finding ref:** SEC-15, CA-10

## 2026-10-26 · Parallel confirmations created duplicate records
- **Symptom:** two simultaneous "yes" messages for the same pending contact (double click, two tabs) both saved it.
- **Root cause:** each request read the CONFIRMING context from Redis, ran the turn and wrote it back with no lock.
- **Fix:** `session_lock()` (Redis `SET NX PX 30000`, owner-checked delete, fails open with a warning) in `backend/app/services/session_manager.py:142`, held for the whole turn in `send_message` (`backend/app/routers/chat.py:215`); a busy session answers 409 (`chat.py:287`). The lock is taken after the ownership check, so nobody can lock another user's session.
- **Verification:** `test_concurrent_confirm_single_entity` returns `[200, 409]` and one contact; with the lock replaced by a no-op the same test gets `[200, 200]`.
- **Finding ref:** SEC-08

## 2026-10-26 · A bad AI value turned the save into a 500 and lost the messages
- **Symptom:** when the model produced e.g. `stage="won"`, the save failed, the failure path inserted `ChatAction(status="failed", entity_type="unknown")` which violated the CHECKs, the later commit raised, the request returned 500 and neither chat message was stored.
- **Root cause:** writes ran in the request transaction with no savepoint; the CHECK from migration 0005 had no `failed` status.
- **Fix:** each save runs in `async with db.begin_nested()` (`backend/app/routers/chat.py:472`); entity type is derived from the intent before the attempt; migration `0009_chat_action_failed.py` adds `failed` (model CHECK in `models/chat.py`); the user gets a clarification, the context goes back to COLLECTING without the rejected fields (`chat.py:250-260`).
- **Verification:** `test_bad_deal_gives_clarification[stage|value 5k|value -10|unknown key]`: 200, both messages stored, one `failed` deal action, no deal; `tests/test_migrations.py` round-trips 0008-0009.
- **Finding ref:** SEC-06, CA-03

## 2026-10-26 · LLM output written to the database unvalidated; fuzzy and silent update targets
- **Symptom:** any key or value from the model reached the DB (`stage="won"`, `value="5k"`, injected `_entity_id`); "update John" could change "Johnson"; an update for a missing name silently created a new record; chat activities were always `note` (schema key `activity_type`, saver read `type`); tags, expected close, `source` and `ai_session_id` were never stored.
- **Root cause:** `{**already, **extracted}` merge accepted every key; `_save_entity` used `data.get(...)`, `float(...)`, `ilike('%name%') LIMIT 1` and a create fallback.
- **Fix:** per-intent Pydantic models with `extra="forbid"`, `Literal` stages/types, bounded strings and `Decimal` money (`backend/app/schemas/ai_actions.py`); extractor keeps only schema keys (`services/ai_engine/data_extractor.py:83`); targets resolved by case-insensitive exact match, else a clarification naming the missing or ambiguous record (`routers/chat.py:497-525`); writers set `type=activity_type`, tags, `expected_close`, `source="ai_chat"`, `ai_session_id` (`chat.py:538-596`).
- **Verification:** `test_extract_schema_forbids_unknown_keys`, `test_update_not_found_asks_instead_of_creating`, `test_update_uses_exact_name`, `test_update_ambiguous_name_lists_candidates`, `test_activity_type_mapped`, `test_contact_provenance_and_tags`, `test_deal_fields_persisted`.
- **Finding ref:** SEC-05, CA-05, CA-06, CA-07

## 2026-10-26 · "no, don't save" saved the record
- **Symptom:** replies such as "no, don't save", "not ok" or "change the email, ok?" created the entity.
- **Root cause:** `_handle_confirming` tested affirmative words before negative ones, and "save"/"ok" appear in those refusals.
- **Fix:** `parse_confirmation()` checks negating or hedging words first ("no", "not", "don't", "do not", "but", "change", ...) (`backend/app/services/ai_engine/orchestrator.py:48`), used by `_handle_confirming`. Interim; the Phase 1 confirm endpoint replaces free-text saving.
- **Verification:** `tests/test_confirmation.py::test_confirmation_parser` (25 utterances) and `tests/test_save_entity.py::test_no_dont_save_saves_nothing`.
- **Finding ref:** SEC-04, CA-04

## 2026-10-26 · Weak registration and login hygiene
- **Symptom:** 3-character passwords accepted; `Bob@x.io` and `bob@x.io` could both register; a duplicate email returned "Email already registered" (account enumeration) and a parallel duplicate raised an unhandled `IntegrityError` (500); unknown-email logins returned faster than wrong-password logins; a failure between the user commit and stage seeding left a user without pipeline stages.
- **Root cause:** `password: str` with no bounds (bcrypt ignores bytes past 72); emails stored as typed; check-then-insert in `register`; `login` skipped bcrypt when the user was missing; two commits in `register`.
- **Fix:** password 10-72 UTF-8 bytes and lower-cased `NormalizedEmail` (`backend/app/schemas/user.py:10,20`); migration `0008_lower_email_unique.py` lower-cases rows and adds unique index on `lower(email)` (also in `models/user.py`); `register` flushes and maps `IntegrityError` to a generic 409, then seeds stages in the same transaction (`backend/app/routers/auth.py:24-42`); `login` always runs bcrypt, against `DUMMY_HASH` for unknown users (`auth.py:49`, `services/auth_service.py:25`).
- **Verification:** `tests/test_auth.py` (`test_register_case_insensitive_duplicate`, `test_register_password_policy[6 cases]`, `test_lower_email_unique_index`, `test_login_ok_case_insensitive`, `test_login_unknown_user_does_hash`) failed before, pass after; `tests/test_migrations.py` round-trips 0008.
- **Finding ref:** SEC-12, CA-14

## 2026-10-26 · No rate limiting on login, register, chat or insights
- **Symptom:** unlimited login attempts (credential stuffing), account spam and unbounded LLM spend through chat and insights; all clients appeared as the nginx IP.
- **Root cause:** no limiter anywhere; uvicorn started without `--proxy-headers`.
- **Fix:** `backend/app/services/rate_limit.py` (Redis fixed window, dependency factory, 429 + `Retry-After`, fails open with a warning) on login 5/min per IP+email (`routers/auth.py:45`), register 3/h per IP (`auth.py:22`), chat 30/min per user (`routers/chat.py:172`), insights 10/h per user (`routers/ai.py:53`); shared client `services/redis_client.py`; nginx `limit_req` zones `auth` 10 r/min and `api` 20 r/s (`nginx/nginx.conf`); `--proxy-headers --forwarded-allow-ips='*'` (`backend/Dockerfile:33`).
- **Verification:** `test_rate_limit_login` (6th → 429, Retry-After ≤ 60, key TTL set), `test_rate_limit_login_is_per_email`, `test_rate_limit_register`, `test_rate_limit_chat_user_budget`, `test_rate_limit_insights`, `test_rate_limit_fails_open` failed before, pass after; `nginx -t` ok.
- **Finding ref:** SEC-03

## 2026-10-26 · Chat held a pooled DB connection across every LLM round-trip
- **Symptom:** with a 2-connection pool, 6 parallel slow chat messages failed with `QueuePool limit of size 2 overflow 0 reached` (500s); ~30 concurrent chats would starve every endpoint in production (pool 10+20).
- **Root cause:** `send_message` ran its first query, which opened a transaction, then called the orchestrator (up to 3 LLM calls) before committing, so the connection stayed checked out for the whole LLM time.
- **Fix:** verify session -> `await db.commit()` to release the connection (`backend/app/routers/chat.py:195`) -> LLM call -> messages and entity saved in one short transaction (`chat.py:224-259`).
- **Verification:** `tests/test_chat_concurrency.py::test_pool_not_held_during_llm` (pool 2, 6 chats, 0.6 s per LLM call) failed with pool timeouts before, passes after.
- **Finding ref:** SEC-07, CA-02

## 2026-10-26 · Synchronous Bedrock call froze the whole API during chat
- **Symptom:** while 5 chat messages waited on a slow LLM, `/api/health` and every other request stalled for seconds.
- **Root cause:** `send_message` called the sync `Orchestrator.process_message` (boto3 `converse`) directly inside the async handler, blocking the single event loop; boto3 used 60 s default timeouts and retries; nothing capped concurrent LLM calls.
- **Fix:** `await asyncio.to_thread(...)` inside `async with llm_slots` (`backend/app/routers/chat.py:200-203`, title task `:363`, insights `backend/app/routers/ai.py:90`); `llm_slots = asyncio.Semaphore(8)` and boto3 `Config(connect_timeout=3, read_timeout=15, retries={"max_attempts": 2})` (`backend/app/services/bedrock_service.py:22-32`); background title tasks kept in `_background_tasks` so they are not garbage-collected (`chat.py:44,273`, CA-25). Interim until the Phase 1 async provider.
- **Verification:** `test_chat_does_not_block_loop` (5 chats, 1 s fake LLM delay, health worst case < 100 ms) and `test_bedrock_client_has_timeouts` fail before, pass after.
- **Finding ref:** SEC-02, CA-01

## 2026-10-26 · Postgres and pgAdmin published with committed default passwords
- **Symptom:** `docker compose up` published Postgres on `0.0.0.0:5435` and pgAdmin on `0.0.0.0:5050`; pgAdmin's password was hard-coded in `docker-compose.yml`, and the DB password was committed in `.env.example`, `backend/.env.example` and `docs/pgadmin_setup.md`.
- **Root cause:** dev conveniences (host ports, inline credentials, `:latest` image) shipped in the default compose profile; no secret scanning.
- **Fix:** removed `db.ports` (`docker-compose.yml:13`); pgAdmin moved to `profiles: ["dev"]`, bound to `127.0.0.1:5050`, credentials from `.env`, image pinned to `9.18` (`docker-compose.yml:76-84`); Postgres/Redis images pinned to `16.15-alpine`/`7.4.11-alpine`; `change-me` placeholders in `.env.example:6,8,11,18`; `backend/.env.example` deleted (duplicate, CA-29); `docs/pgadmin_setup.md:10,20,42` uses env names; gitleaks pre-commit hook `v8.30.1` (`.pre-commit-config.yaml`); policy script `scripts/check_compose_policy.py`. Lebi action: rotate any real `.env` that reused the old values.
- **Verification:** `python3 scripts/check_compose_policy.py` failed with 9 violations before, prints `compose policy: ok` after; `gitleaks git` over 16 commits: no leaks found.
- **Finding ref:** SEC-01

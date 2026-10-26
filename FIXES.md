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

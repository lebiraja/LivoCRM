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

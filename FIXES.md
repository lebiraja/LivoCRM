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

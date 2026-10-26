# 05 - Testing Plan

Purpose: what to test, fixtures, Docker commands and coverage targets for LivoCRM (backend pytest, frontend vitest, E2E Playwright).
Date: 2026-10-26 | Status: proposed (current state: zero tests, zero CI) | Convention: tests run in Docker, never on a global Python install.

## 1. Strategy
| Level | Tool | Scope | Runs in |
|---|---|---|---|
| Unit | pytest | pure functions: validators, fallbacks, rate limiter, guard, confirmation parser, scoring, JWT helpers | Docker `backend` image |
| API / integration | pytest + pytest-asyncio + httpx `AsyncClient` (ASGI transport) + real Postgres + fakeredis | routers, ownership, transactions, migrations | Docker with `db-test` |
| WebSocket | Starlette `TestClient.websocket_connect` | auth ticket, ownership, cleanup | Docker |
| AI | `FakeLLMProvider` + `httpx.MockTransport` (Groq) | orchestrator flows, failure matrix | Docker |
| Frontend unit/component | vitest + @testing-library/react + MSW + Zod | stores, hooks, pages, forms | Node container |
| E2E | Playwright | login -> main journeys against the compose stack with `LLM_PROVIDER=fake` | host or Playwright image |
| Static | ruff, mypy, `tsc -b`, eslint, gitleaks, pip-audit, npm audit | every PR | CI |

No test calls Groq, AWS, or any external service. A `live` marker exists for manual evaluation only (`pytest -m live`, excluded by default).

## 2. Backend test inventory (priority order)

### 2.1 Auth (target 95%+ line and branch coverage) - `tests/api/test_auth.py`, `tests/unit/test_auth_service.py`
- Register: ok; duplicate email (case-insensitive); invalid email; password too short/long/72-byte boundary/unicode; response never contains `hashed_password`; default pipeline stages seeded exactly once; `IntegrityError` race -> 409 not 500 (parallel registrations).
- Login: ok; wrong password; unknown email (same status/body, similar timing: assert dummy hash executed via monkeypatch counter); rate limit 429 after N attempts with `Retry-After`; lockout window expires (fakeredis time).
- Token: expired -> 401; tampered signature -> 401; `alg=none` -> 401; wrong key -> 401; missing `sub` -> 401; non-UUID `sub` -> 401 (not 500); token for deleted user -> 401; `jti` deny-list after logout (when added).
- `/auth/me` requires auth; returns only public fields.

### 2.2 Authorization / tenancy (cross-tenant matrix) - `tests/api/test_tenancy.py`
Two users A and B (later: two workspaces and roles owner/staff/viewer). For each resource (contacts, deals, activities, pipeline stages, chat sessions, appointments/follow-ups after Phase 2): B cannot GET/PATCH/DELETE/list A's ids (404, never 403/200), list endpoints never leak A's rows, `search`/filters cannot widen scope, writes referencing A's `contact_id`/`deal_id` (SEC-09) -> 404, `/ai/score/{A.contact}` -> 404, WS ticket for A cannot subscribe to B's session, analytics numbers exclude other tenant. Parametrize over (resource, verb).
Role tests (Phase 2): viewer cannot write, staff cannot delete or change roles, owner can; role change takes effect on next request.

### 2.3 Data mutations (target 90%+ on routers/services that write) - `tests/api/test_contacts.py`, `test_deals.py`, `test_activities.py`, `tests/services/test_save_entity.py`
- Create/update/delete happy paths; `PATCH` partial update leaves other fields; unset vs null semantics (`exclude_unset`).
- Validation (parametrized, expect 422 not 500): oversize strings, bad email, negative value, invalid stage/status/type, extra fields rejected where `extra="forbid"`, huge `tags`.
- Deal stage transitions: `closed_won` sets status `won`, `closed_lost` sets `lost`; moving back to open stage resets status to `active` (currently untested behaviour; decide and encode); invalid stage 422.
- Delete semantics: deleting a contact nulls `deals.contact_id` and `activities.contact_id` (migration 0007); deleting a user cascades everything; deleting a session removes messages and actions.
- Transactions: failure after partial write leaves no rows (force an exception mid-request via monkeypatch); `IntegrityError` mapped to 409.
- Pagination: `skip/limit` bounds, `total` accurate with search, ordering stable.
- Concurrency: two parallel PATCHes do not corrupt; double delete second returns 404.

### 2.4 AI engine - `tests/ai/*` (see also `04-groq-migration.md` section 4)
- Confirmation parser table (20+ utterances) including SEC-04 cases: `no don't save`, `not ok`, `yes but change the email`, `ok`, `yep go ahead`, Tamil/Tanglish confirmations (`seri`, `venam`) `[?]` per product decision; after the confirm endpoint exists, free-text never saves.
- Orchestrator state machine: IDLE->COLLECTING->CONFIRMING->SAVING->IDLE with `FakeLLMProvider` scripts; interrupted flows; MULTI_INTENT; QUERY_DATA; follow-up detection no longer triggers on generic words.
- `_save_entity`: bad stage, bad value, unknown keys, activity type mapping, not-found update (asks instead of creating), ambiguous name (returns candidates), provenance fields set, `ChatAction` rows legal, no 500 on any model output (property test with Hypothesis over random dict payloads).
- Concurrency: parallel confirms -> one entity (lock); context lost -> graceful restart.
- Prompt-injection regression set (`tests/ai/injection.yaml`): messages containing "ignore previous instructions", fake JSON, `_entity_id`, delimiter-closing tags; assert schema validation drops them and no write happens without confirm.
- Logging: caplog contains no phone/email for any failure path.
- Guard: budgets, circuit breaker, timeouts (with `FakeClock`).

### 2.5 Infrastructure behaviours
- Rate limiter unit + route tests (SEC-03).
- Health: `/api/health` ok; deep health reports db/redis state (when implemented).
- Migrations: `alembic upgrade head` on empty DB, `downgrade -1` round trip for each new revision, and upgrade on a DB seeded with pre-0008 data (constraint changes must not fail).
- Event loop: slow fake provider does not delay `/api/health`.
- WebSocket: ticket single use, expiry, wrong user, ownership, cleanup on abrupt close.
- Config: startup fails with short `SECRET_KEY`, missing `GROQ_API_KEY` when provider=groq, placeholder secrets rejected.

## 3. Fixtures (backend `tests/conftest.py`)
| Fixture | Purpose |
|---|---|
| `db_engine` (session scope) | creates schema via `alembic upgrade head` once on `db-test` (tmpfs-backed Postgres 16) |
| `db` (function) | connection + outer transaction, `AsyncSession` bound with `join_transaction_mode="create_savepoint"`, rollback after test |
| `app` / `client` | FastAPI app with `get_db` overridden; `httpx.AsyncClient(transport=ASGITransport(app))` |
| `redis` | `fakeredis.aioredis.FakeRedis` injected into session manager, limiter, guard |
| `llm` | `FakeLLMProvider` with scripted queue per test; asserts all scripted responses consumed |
| `clock` | injectable clock for limiter, circuit breaker, recovery scheduler |
| `make_user`, `auth_headers` | factory creating user (+workspace/role later) and a valid JWT |
| `factories` | `ContactFactory`, `DealFactory`, `ActivityFactory`, `AppointmentFactory` (plain async helpers or `polyfactory`) |
| `freeze_time` | `time-machine` for token expiry and no-show rules |
Dev requirements (`backend/requirements-dev.txt`, pinned): pytest, pytest-asyncio, pytest-cov, httpx, fakeredis, respx or MockTransport (httpx built-in), time-machine, hypothesis, ruff, mypy, pip-audit. `pytest.ini`: `asyncio_mode = auto`, markers `live`, `slow`; default `-m "not live"`.

## 4. Frontend tests (vitest)
Setup: `vitest`, `@testing-library/react`, `@testing-library/user-event`, `jsdom`, `msw`, `@vitest/coverage-v8`; scripts `test`, `test:cov`; `vite.config.ts` `test` block; MSW handlers mirror the OpenAPI schema (generate types from `/openapi.json` to keep contract tests honest).
| Area | Cases |
|---|---|
| `api/client` | adds Bearer header; 401 clears token and redirects once; network error surfaces |
| Zod boundary | every response schema parses fixtures; unknown extra fields tolerated; bad shape throws a typed error shown as toast |
| `authStore` | login stores token, fetchUser failure logs out, logout clears state |
| `useWebSocket` | connects with ticket, reconnect backoff, **no reconnect after unmount/session change** (CA-17), cleanup |
| `useChat` | send success, error message, degraded flag, confirm/cancel calls endpoint, no `local-` sessions |
| Pages | Today queue approve/skip/snooze optimistic update + rollback on 500; Contacts form validation and error toasts (no silent catch); Pipeline/Kanban drop calls API and reverts on failure; INR formatting; Tamil strings render; empty/error/loading states |
| A11y | `jest-axe` on main pages |
Coverage target: 70% lines overall, 90% on stores/hooks/api modules.
Playwright (E2E, `LLM_PROVIDER=fake`, seeded DB): register/login; create contact; chat add-contact flow with confirm button; approve a follow-up draft and see it in the log; no-show appears in queue after seeded time; mobile viewport 390 px smoke; offline-fonts check (no external requests via `page.on('request')`).

## 5. Docker commands
Compose additions (Phase 0): service `db-test` (`postgres:16-alpine`, tmpfs, healthcheck, profile `test`), backend `test` service or override using the same image with dev deps.
```bash
# backend: full suite with coverage (no external network required)
docker compose --profile test run --rm backend pytest -q --cov=app --cov-report=term-missing --cov-fail-under=80

# focused runs
docker compose --profile test run --rm backend pytest tests/api/test_auth.py -q
docker compose --profile test run --rm backend pytest -k "tenancy or confirmation" -q
docker compose --profile test run --rm backend pytest -m live -q        # manual eval only, needs GROQ_API_KEY

# static checks
docker compose --profile test run --rm backend sh -c "ruff check app tests && mypy app"
docker compose --profile test run --rm backend pip-audit -r requirements.txt

# frontend
docker compose --profile test run --rm frontend-test npm run test:cov
docker compose --profile test run --rm frontend-test sh -c "npx tsc -b && npx eslint ."

# e2e (stack up with fake LLM, then Playwright)
LLM_PROVIDER=fake docker compose up -d --build
docker run --rm --network host -v "$PWD/e2e:/e2e" -w /e2e mcr.microsoft.com/playwright:v1.50.0-jammy npx playwright test   # version tag [?] pin to the project's installed version
```
Note: `docker compose up` and these runs are for the implementation phase; this audit did not run any of them.

## 6. Coverage targets and gates
| Area | Target | Gate |
|---|---|---|
| `services/auth_service.py`, `routers/auth.py`, `dependencies.py`, rate limiter | >= 95% lines, 90% branches | CI fail |
| Routers that mutate data (contacts, deals, activities, appointments, follow-ups, templates, messages, chat confirm) + `_save_entity` | >= 90% lines | CI fail |
| `services/llm/*`, `ai_engine/*` | >= 90% lines | CI fail |
| Backend overall | >= 80% lines | CI fail (`--cov-fail-under=80`) |
| Frontend overall | >= 70% lines; stores/hooks/api >= 90% | CI fail |
| Mutation spot check (optional) | `mutmut` on `confirmation parser` and `auth_service` | manual |
| Static | zero ruff errors, mypy clean on `app/services/llm` and new code, `tsc` strict clean, zero `any` | CI fail |
| Security | gitleaks clean, `pip-audit`/`npm audit` no high/critical unresolved | CI fail |

## 7. Regression tests mapped to audit findings
| Finding | Test |
|---|---|
| SEC-01 | `tests/infra/test_compose_policy.py`: parse `docker compose config --format json`; no host port on `db`; no literal passwords; images pinned |
| SEC-02 / CA-01 | `test_chat_does_not_block_loop` |
| SEC-03 | `test_rate_limit_login`, `test_rate_limit_chat_user_budget` |
| SEC-04 / CA-04 | `test_confirmation_parser[...]`, `test_free_text_yes_does_not_save` |
| SEC-05 / CA-06 | `test_extract_schema_forbids_unknown_keys`, `test_bad_stage_gives_clarification` |
| SEC-06 / CA-03 | `test_save_failure_persists_messages_and_action_failed` |
| SEC-07 | `test_pool_not_held_during_llm` |
| SEC-08 | `test_concurrent_confirm_single_entity` |
| SEC-09 | `test_cross_tenant_fk_reference_rejected` |
| SEC-10 / SEC-19 | `test_ws_ticket_single_use`, `test_ws_chat_ownership` |
| SEC-12 | `test_register_case_insensitive_duplicate`, `test_login_unknown_user_does_hash` |
| SEC-13 | `test_no_pii_in_logs` |
| SEC-14 | `test_invalid_payloads_return_422[...]` |
| SEC-15 / CA-10 | `test_event_published_after_commit` |
| CA-05 | `test_activity_type_mapped`, `test_ai_provenance_set` |
| CA-13 | `test_context_survives_process_restart` (clear in-memory, keep fakeredis) |
| CA-17 (frontend) | `useWebSocket.test.ts: no reconnect after unmount` |
| CA-23 | migration test + `EXPLAIN` assertion uses index for phone lookup |

## 8. Order of work
1. Harness + smoke (P0.0). 2. Auth + tenancy tests written first, then Phase 0 fixes turn them green. 3. Mutation/validation suite with P0.5/P0.9. 4. AI suite with Phase 1. 5. Frontend harness at start of Phase 3, pages as they are rebuilt. 6. CI wiring and coverage gates in Phase 4. 7. E2E last, against the final UI.

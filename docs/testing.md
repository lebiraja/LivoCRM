# Testing

Four suites. Counts are from `STATUS.md` (v0.5.0-ui) and the source tree; they were not re-run for this
document. Commands assume the repository root.

| Suite | Tool | Count | Coverage | In CI |
|---|---|---|---|---|
| Backend API, services, migrations | pytest 9, pytest-asyncio 1.4, httpx, fakeredis, real Postgres | 232 collected (139 test functions) | 85% (`STATUS.md`) | yes (compose test profile) |
| Frontend | vitest 5, Testing Library 16, jsdom 30, msw 3 | 31 (`STATUS.md`); 8 test files | not measured | no |
| Cloud (Lambdas, ML, export) | pytest 8.3 | 38 (`STATUS.md`); 7 test files | not measured | yes (`pytest -q`) |
| End-to-end | none | 0 | - | no |

## Backend

Location: `backend/tests/`. Config: `backend/pytest.ini` (`asyncio_mode = auto`; `-m "not live"` by default).

- **Database.** Tests run against a real Postgres at `TEST_DATABASE_URL`. A session fixture drops and recreates
  the `public` schema, then runs `alembic upgrade head`. Each test uses a connection with an outer transaction
  that is rolled back.
- **Redis.** `fakeredis` (async) replaces the client.
- **LLM.** `tests/fakes.py` `FakeLLMProvider` replaces `chat_completion`. Tests never call Groq or Bedrock.
- **HTTP.** `httpx.AsyncClient` over `ASGITransport` against the real FastAPI app.
- **Markers.** `live` (declared for real-service calls; no test carries it). `slow` (two `test_save_entity` cases).

Modules (18 files):

| Module | Covers (from test names) |
|---|---|
| `test_auth.py` | register and login rules, case-insensitive email, password policy, login rate limit per IP+email, register limit, chat and insights budgets, limiter fails open |
| `test_tokens.py` | `iat` and unique `jti`; expired, tampered, `alg=none`, wrong-key and missing-`iat` tokens get 401 |
| `test_tenancy.py` | cross-tenant foreign keys rejected; own references allowed (SEC-09) |
| `test_validation.py` | invalid payloads get 422; duplicate stage name 409; `DataError` mapping; non-UUID `sub` 401 |
| `test_hardening.py` | PII redaction in logs and uvicorn handler; `generated_by` hides model id; `%` and `_` escaped; docs off; CORS from env |
| `test_chat_concurrency.py` | event loop not blocked during chat; DB pool not held across LLM calls; Bedrock client timeouts (SEC-02, SEC-07) |
| `test_confirmation.py` | 25-utterance confirmation parser table |
| `test_save_entity.py` | "no, don't save" saves nothing; provenance and tags; savepoint clarification; exact-name updates; ambiguous names; schema rejects unknown keys; concurrent confirm yields one row; event after commit |
| `test_session_context.py` | context survives restart; bound to user; fresh context when Redis is down |
| `test_ws.py` | ticket contract; single use; raw JWT rejected; bound to user and session; 5-socket cap; cleanup after loop error |
| `test_appointments.py` | create and list (range, status filter); cross-user 404; invalid input 422 |
| `test_follow_ups.py` | list and filters; draft via LLM or template fallback; no patient identifiers in prompt; approve creates exactly one message; draft after approval 409 |
| `test_recovery.py` | reminder timing (24 h, 2 h); 1 h no-show grace; closed statuses ignored; second run creates nothing; tenant isolation; scheduler covers all users; summary attribution |
| `test_demo_seed.py` | endpoint and CLI seed; idempotent; scoped per user; CLI rejects unknown email |
| `test_groq.py` | key parsing and dedupe; duration parsing; key id hides secret; 429 fails over without sleeping; cooldown expiry; 401 disables only that key; 5xx retried; selection by remaining tokens, then LRU; no-key error |
| `test_migrations.py` | 0008 to 0010 round-trip; clinic tables drop and restore |
| `test_quick_wins.py` | lead score uses days since last activity; extractor prompt braces |
| `test_health.py` | `/api/health` returns ok |

Commands:

```bash
# Full suite in Docker (throwaway Postgres on tmpfs)
docker compose run --rm --build backend-test pytest

# CI form (explicit profile)
docker compose --profile test run --rm --build backend-test pytest

# Coverage: pytest-cov is in requirements-dev.txt; the flags are not in pytest.ini
docker compose run --rm --build backend-test pytest --cov=app --cov-report=term-missing

# Lint and types in the test image (ruff.toml present; mypy has pre-existing errors, not a gate)
docker compose run --rm --build backend-test ruff check .
docker compose run --rm --build backend-test mypy app
```

The `ruff` and `mypy` commands use the test image's installed tools. They were not run for this document.
`mypy` reported 22 errors at v0.2.0 (`STATUS.md`).

## Frontend

Location: `frontend/src/**/*.test.ts(x)`. Setup: `frontend/src/test/setup.ts`, MSW server in `frontend/src/test/server.ts`.

| File | Covers (from test names) |
|---|---|
| `hooks/useWebSocket.test.ts` | ticket fetched before connect, JWT kept out of URL; fresh ticket on each reconnect; retry after 4002; no reconnect after unmount |
| `i18n/LanguageToggle.test.tsx` | EN/TA switch, `<html lang>`, persistence; every English key has a Tamil string |
| `lib/ai-health.test.ts` | flattening the AI pool response into one row per key; unused key shows as ready |
| `lib/format.test.ts` | rupee formatting, lakh and crore grouping, compact notation |
| `lib/notifyError.test.ts` | error toast text, Tamil fallback |
| `pages/TodayPage.test.tsx` | follow-up rows, approve and skip through the API, empty and retry states |
| `pages/AppointmentsPage.test.tsx` | create sends IST time as UTC; field errors; mark no-show |
| `pages/LoginPage.test.tsx` | sign-in form renders; rejected credentials show an error |

Commands (no compose service; not part of CI):

```bash
cd frontend
npm ci
npm test              # vitest run
npm run lint          # eslint
npm run build         # tsc -b && vite build
```

To run without a host Node install, use a throwaway container [?] (not run for this document):
`docker run --rm -v "$PWD:/app" -w /app node:20-alpine sh -c "npm ci && npm test"`.

## Cloud

Location: `cloud/`. Config: `cloud/pytest.ini` (`testpaths = lambdas tests`, both Lambda source trees on `pythonpath`).

| Path | Covers (from test names) |
|---|---|
| `lambdas/etl/tests/test_etl_transform.py` | Kaggle and LivoCRM header detection; bad-row drop counts; feature engineering; age bands; UTC conversion; Hive-style keys; Parquet round trip |
| `lambdas/etl/tests/test_etl_handler.py` | S3 event (SSE, URL-decoded keys); schedule picks newest export; fails loudly with none |
| `lambdas/score/tests/test_score_scoring.py` | feature columns match training; UTC handling; invalid timing, age and batch size rejected; artifact with wrong features rejected |
| `lambdas/score/tests/test_score_handler.py` | direct invoke writes nothing; scheduled run writes results; model cached per container; bad payload rejected |
| `tests/test_feature_parity.py` | feature names agree across ETL, scorer and trainer; age bands agree at every boundary |
| `tests/test_train.py` | both candidates trained with metrics written; missing columns and empty channel fail fast |
| `tests/test_export_anonymised.py` | outcomes only; ids hashed with a key; no names, phones or notes in output; short or missing key refused |

```bash
python3 -m venv ~/.venvs/livocrm-cloud
~/.venvs/livocrm-cloud/bin/pip install -r cloud/requirements-test.txt
cd cloud && ~/.venvs/livocrm-cloud/bin/pytest -q
```

Run in a venv outside the repo, as CI does. The Lambda handler tests replace the module-level S3 client with an
in-test fake (`FakeS3`), so they need no AWS credentials.

## Other checks

- `python3 scripts/check_compose_policy.py`: ports, healthchecks, `env_file`, secret references and image tags in
  `docker-compose.yml`. Needs the docker CLI.
- gitleaks: `.pre-commit-config.yaml` runs the gitleaks hook (v8.30.1). Install with `pre-commit install` if you
  commit from the host.
- CI (`.github/workflows/deploy.yml`, manual trigger): runs the cloud suite and the backend compose test profile.
  The frontend suite is not in CI.

## Not covered

- No browser E2E suite (Playwright is planned in `docs/plan/05-testing-plan.md`, not written).
- No test calls a real LLM or AWS service.
- Tamil and Tanglish output quality is not evaluated. No eval set exists.
- Frontend coverage is not measured. Backend coverage is only reported in `STATUS.md`.

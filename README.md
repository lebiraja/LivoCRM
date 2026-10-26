# LivoCRM

A single-owner CRM with an AI chat assistant. Keep contacts, deals, activities and a Kanban pipeline; ask
"Livo" in chat to add or update records, and confirm before anything is saved. A clinic follow-up desk
sits on the same codebase: appointments, a follow-up queue with English and Tamil message drafts, and a
no-show recovery engine. Everything runs with Docker Compose. AI is optional: without a Groq key, every
AI feature falls back to deterministic behaviour.

## Quickstart

Requires Docker with Compose v2.

```bash
cp .env.example .env                 # then replace every change-me; SECRET_KEY >= 32 chars
docker compose up -d --build         # db, redis, backend, frontend, nginx
curl -fsS http://localhost:3500/api/health
```

Open <http://localhost:3500>, register, then load the demo clinic data:

```bash
docker compose exec backend python -m app.cli seed-demo --email you@example.com
```

Add Groq keys with `GROQ_API_KEYS` in `.env` to enable the AI features. Keys from one Groq organisation share a
rate limit. Stop with `docker compose down`.

## Tests

```bash
docker compose run --rm --build backend-test pytest       # backend, 232 collected tests
(cd cloud && pytest -q)                                   # cloud Lambdas and ML, in a venv
```

Frontend tests (`npm test` in `frontend/`) and the suite breakdown are in [docs/testing.md](docs/testing.md).

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic 2, PyJWT
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS 4, shadcn/ui, Zustand, React Router
- **Data:** PostgreSQL 16, Redis 7.4 (chat state, rate limits, WebSocket tickets)
- **AI:** Groq (OpenAI-compatible; `openai/gpt-oss-20b` and `openai/gpt-oss-120b`), local RandomForest lead score
- **Edge and infra:** Nginx, Docker Compose, healthchecks on every default service
- **Cloud (offline, not deployed):** AWS SAM, Lambda, S3, SageMaker, GitHub Actions OIDC

## Documentation

| Doc | What it covers |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Services, request flows, auth and WebSocket tickets, chat confirm flow, recovery engine, data model (ER diagram) |
| [docs/docker.md](docs/docker.md) | Compose services, profiles, ports, healthchecks, environment variables, run and test commands |
| [docs/API.md](docs/API.md) | Every `/api` route with auth, body, response, errors and rate limits; WebSocket contract |
| [docs/ai.md](docs/ai.md) | LLM providers, Groq key pool, failover, health endpoint, fallbacks |
| [docs/security.md](docs/security.md) | Security findings (SEC-01 to SEC-29) with status and where each is enforced |
| [docs/testing.md](docs/testing.md) | Test suites, counts, commands and what is not covered |
| [docs/cloud/architecture.md](docs/cloud/architecture.md) | AWS no-show pipeline: ETL, SageMaker training, scoring, analytics (not deployed) |
| [docs/plan/](docs/plan/) | Audit, security review and implementation plans for the IA3 build |
| [docs/archive/](docs/archive/) | Earlier DBMS submission and old guides. Not current |

Project tracking lives in `HANDOVER.md`, `STATUS.md`, `FIXES.md`, `CHECKLIST.md` and `VERSIONS.md`.

## Repository layout

```text
backend/    FastAPI app, Alembic migrations, ML training scripts, pytest suite
frontend/   React SPA, built by Vite and served by nginx:alpine
nginx/      Edge gateway: routing, rate limits, security headers
cloud/      AWS SAM template, ETL and score Lambdas, SageMaker training code
docs/       Architecture, API, Docker, AI, security and testing docs
scripts/    Compose policy check
```

## Status

IA3 build. The app and its tests run locally with Docker. The AWS pipeline in `cloud/` is written and
unit-tested but has not been deployed. Tamil copy has not been reviewed by a native speaker, and no
browser end-to-end suite exists yet.

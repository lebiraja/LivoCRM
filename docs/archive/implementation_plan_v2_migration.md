# Replace Django Backend with FastAPI + Nginx Reverse Proxy

Replace the existing Django/DRF backend with a FastAPI async backend, add an Nginx reverse proxy, and update Docker Compose to orchestrate all 5 services.

## User Review Required

> [!IMPORTANT]
> The existing [.env](file:///home/lebi/projects/livocrm/.env) contains **live AWS credentials** (access key, secret). These will be preserved in the new [.env](file:///home/lebi/projects/livocrm/.env) but removed from [.env.example](file:///home/lebi/projects/livocrm/.env.example). Make sure to rotate these keys if they've been committed to git.

> [!WARNING]
> This **deletes everything inside `backend/`** (Django code, migrations, [manage.py](file:///home/lebi/projects/livocrm/backend/manage.py), `livocrm_backend/`, `apps/`). The ML script [ml/train_lead_scorer.py](file:///home/lebi/projects/livocrm/backend/ml/train_lead_scorer.py) will be replaced with two new scripts: `ml/generate_data.py` and `ml/train_scorer.py`.

## Proposed Changes

### 1. Cleanup — Delete Django backend

#### [DELETE] `backend/apps/` — all Django apps
#### [DELETE] `backend/livocrm_backend/` — Django settings
#### [DELETE] `backend/manage.py` — Django CLI
#### [DELETE] `backend/app/` — empty skeleton dirs

Keep `backend/ml/` content for reference, then replace.

---

### 2. Backend Core — FastAPI application

#### [NEW] [main.py](file:///home/lebi/projects/livocrm/backend/app/main.py)
- FastAPI app with `/api` prefix, CORS for `localhost:5173` and `localhost`
- Registers all routers: auth, contacts, deals, activities, analytics, ai

#### [NEW] [config.py](file:///home/lebi/projects/livocrm/backend/app/config.py)
- `pydantic-settings` BaseSettings reading `DATABASE_URL`, `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REDIS_URL` from `.env`

#### [NEW] [database.py](file:///home/lebi/projects/livocrm/backend/app/database.py)
- `create_async_engine` + `async_sessionmaker` + `AsyncSession`
- `Base` declarative base for all models

#### [NEW] [dependencies.py](file:///home/lebi/projects/livocrm/backend/app/dependencies.py)
- `get_db()` — async generator yielding `AsyncSession`
- `get_current_user()` — JWT bearer dependency extracting user from token

---

### 3. Models — SQLAlchemy 2.0 async

All models use UUID PK via `server_default=text("gen_random_uuid()")` and include `created_at`/`updated_at` timestamps.

#### [NEW] [user.py](file:///home/lebi/projects/livocrm/backend/app/models/user.py)
- `id` (UUID), `email` (unique), `hashed_password`, `full_name`, `plan` (free/pro/business)

#### [NEW] [contact.py](file:///home/lebi/projects/livocrm/backend/app/models/contact.py)
- `id`, `user_id` (FK→users), `name`, `email`, `phone`, `company`, `tags` (JSON), `lead_score`, `notes`

#### [NEW] [deal.py](file:///home/lebi/projects/livocrm/backend/app/models/deal.py)
- `id`, `user_id` (FK), `contact_id` (FK, nullable), `title`, `value` (Numeric), `stage`, `status`, `expected_close`, `notes`

#### [NEW] [activity.py](file:///home/lebi/projects/livocrm/backend/app/models/activity.py)
- `id`, `user_id` (FK), `contact_id` (FK, nullable), `deal_id` (FK, nullable), `type`, `description`, `occurred_at`

#### [NEW] [pipeline.py](file:///home/lebi/projects/livocrm/backend/app/models/pipeline.py)
- `id`, `user_id` (FK), `name`, `position`

---

### 4. Pydantic Schemas (v2)

All schemas use `model_config = ConfigDict(from_attributes=True)`.

#### [NEW] [schemas/user.py](file:///home/lebi/projects/livocrm/backend/app/schemas/user.py)
- `UserCreate`, `UserRead`, `Token`

#### [NEW] [schemas/contact.py](file:///home/lebi/projects/livocrm/backend/app/schemas/contact.py)
- `ContactCreate`, `ContactUpdate`, `ContactRead`

#### [NEW] [schemas/deal.py](file:///home/lebi/projects/livocrm/backend/app/schemas/deal.py)
- `DealCreate`, `DealUpdate`, `DealRead`

#### [NEW] [schemas/activity.py](file:///home/lebi/projects/livocrm/backend/app/schemas/activity.py)
- `ActivityCreate`, `ActivityRead`

#### [NEW] [schemas/pipeline.py](file:///home/lebi/projects/livocrm/backend/app/schemas/pipeline.py)
- `PipelineStageCreate`, `PipelineStageRead`

---

### 5. Routers — API endpoints

#### [NEW] [routers/auth.py](file:///home/lebi/projects/livocrm/backend/app/routers/auth.py)
- `POST /api/auth/register` — create user (public)
- `POST /api/auth/login` — return JWT (public)
- `GET /api/auth/me` — current user (protected)

#### [NEW] [routers/contacts.py](file:///home/lebi/projects/livocrm/backend/app/routers/contacts.py)
- Full CRUD: list (paginated), get, create, update, delete

#### [NEW] [routers/deals.py](file:///home/lebi/projects/livocrm/backend/app/routers/deals.py)
- Full CRUD + `PATCH /api/deals/{id}/stage` for Kanban drag-drop

#### [NEW] [routers/activities.py](file:///home/lebi/projects/livocrm/backend/app/routers/activities.py)
- Full CRUD for activities

#### [NEW] [routers/analytics.py](file:///home/lebi/projects/livocrm/backend/app/routers/analytics.py)
- `GET /api/analytics/summary` — KPI aggregates
- `GET /api/analytics/win-rate` — deal stage funnel
- `GET /api/analytics/forecast` — revenue forecast

#### [NEW] [routers/ai.py](file:///home/lebi/projects/livocrm/backend/app/routers/ai.py)
- `GET /api/ai/score/{contact_id}` — ML lead scoring
- `POST /api/ai/insights` — AI-generated insights

---

### 6. Services

#### [NEW] [services/auth_service.py](file:///home/lebi/projects/livocrm/backend/app/services/auth_service.py)
- `hash_password()`, `verify_password()` via passlib/bcrypt
- `create_access_token()`, `verify_token()` via python-jose

#### [NEW] [services/lead_scoring.py](file:///home/lebi/projects/livocrm/backend/app/services/lead_scoring.py)
- Load `ml/model.pkl`, run inference returning score 0–100

---

### 7. ML Scripts

#### [NEW] [ml/generate_data.py](file:///home/lebi/projects/livocrm/backend/ml/generate_data.py)
- Generate 500 synthetic CRM contacts with Faker + labels

#### [NEW] [ml/train_scorer.py](file:///home/lebi/projects/livocrm/backend/ml/train_scorer.py)
- Train RandomForest, save `model.pkl` (adapts existing `train_lead_scorer.py`)

#### [DELETE] [ml/train_lead_scorer.py](file:///home/lebi/projects/livocrm/backend/ml/train_lead_scorer.py)

---

### 8. Alembic Migrations

#### [NEW] [alembic.ini](file:///home/lebi/projects/livocrm/backend/alembic.ini)
#### [NEW] [alembic/env.py](file:///home/lebi/projects/livocrm/backend/alembic/env.py)
- Async migration runner using `run_async_migrations()`
#### [NEW] [alembic/versions/001_initial.py](file:///home/lebi/projects/livocrm/backend/alembic/versions/001_initial.py)
- Creates all 5 tables: `users`, `contacts`, `deals`, `activities`, `pipeline_stages`

---

### 9. Backend Infrastructure

#### [MODIFY] [requirements.txt](file:///home/lebi/projects/livocrm/backend/requirements.txt)
- Replace Django deps with: fastapi, uvicorn, sqlalchemy, asyncpg, alembic, pydantic-settings, python-jose, passlib, pandas, scikit-learn, numpy, faker, httpx, celery, redis

#### [MODIFY] [Dockerfile](file:///home/lebi/projects/livocrm/backend/Dockerfile)
- `python:3.11-slim`, uvicorn CMD

#### [NEW] [.env.example](file:///home/lebi/projects/livocrm/backend/.env.example)

---

### 10. Nginx Reverse Proxy

#### [NEW] [nginx/nginx.conf](file:///home/lebi/projects/livocrm/nginx/nginx.conf)
- Listen `:80`, route `/api/` → `backend:8000`, `/` → `frontend:5173`
- WebSocket upgrade for Vite HMR, gzip, standard proxy headers

#### [NEW] [nginx/Dockerfile](file:///home/lebi/projects/livocrm/nginx/Dockerfile)
- `FROM nginx:alpine`, copy config

---

### 11. Project Root

#### [MODIFY] [docker-compose.yml](file:///home/lebi/projects/livocrm/docker-compose.yml)
- 5 services: `db` (postgres:15 + healthcheck), `redis` (redis:7-alpine), `backend` (FastAPI), `frontend` (Vite dev), `nginx`

#### [MODIFY] [.env.example](file:///home/lebi/projects/livocrm/.env.example)
- Add `DATABASE_URL`, `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REDIS_URL`
- Remove Django-specific vars

#### [MODIFY] [.env](file:///home/lebi/projects/livocrm/.env)
- Replace Django vars with FastAPI vars, keep AWS creds intact

#### [NEW] [frontend/Dockerfile](file:///home/lebi/projects/livocrm/frontend/Dockerfile)
- `node:20-alpine`, npm install, expose 5173

#### [MODIFY] [README.md](file:///home/lebi/projects/livocrm/README.md)
- Architecture diagram, run instructions, env table

---

## Verification Plan

### Automated Tests
1. `npx tsc --noEmit` in frontend/ — confirm no regressions
2. `docker compose up --build` — all 5 services start
3. `curl http://localhost/api/docs` — Swagger UI loads
4. `curl -X POST http://localhost/api/auth/register` — creates user
5. `curl -X POST http://localhost/api/auth/login` — returns JWT
6. `curl http://localhost` — serves React frontend
7. `docker compose exec backend alembic upgrade head` — migrations run

### Manual Verification
- Browse `http://localhost` → CRM UI loads through Nginx
- Browse `http://localhost/api/docs` → FastAPI Swagger UI
- Browse `http://localhost:8000/docs` → Direct FastAPI access

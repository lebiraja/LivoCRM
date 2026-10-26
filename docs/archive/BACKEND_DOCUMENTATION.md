# Backend Documentation

## 1. Stack and Patterns
- Framework: FastAPI
- ORM: SQLAlchemy 2.0 (async)
- DB driver: `asyncpg`
- Migrations: Alembic
- Auth: JWT (`python-jose`) + bcrypt (`passlib`)
- Validation/serialization: Pydantic v2

## 2. Application Startup
File: `backend/app/main.py`

- Registers a FastAPI lifespan hook that imports `app.models` so metadata is loaded for Alembic context.
- Enables CORS for:
- `http://localhost:5173`
- `http://localhost:3000`
- `http://localhost`
- Mounts routers under `/api`.
- Health endpoint: `GET /api/health`.

## 3. Configuration
File: `backend/app/config.py`

Environment-backed settings:
- `DATABASE_URL`
- `SECRET_KEY`
- `ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REDIS_URL` (declared, not actively used in current code)
- AWS Bedrock keys/model config values (declared, currently not used by AI router logic)

## 4. Authentication and Authorization
Files:
- `backend/app/services/auth_service.py`
- `backend/app/dependencies.py`
- `backend/app/routers/auth.py`

Mechanics:
- Passwords hashed with bcrypt.
- Access token created with JWT `sub=<user_id>` and `exp`.
- `OAuth2PasswordBearer(tokenUrl="/api/auth/login")` used for secured routes.
- `get_current_user` decodes token and loads user by UUID from DB.

Routes:
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`

## 5. Router Reference

### 5.1 Auth Router (`/api/auth`)
- `POST /register`
  - Body: `UserCreate`
  - Behavior: checks email uniqueness, creates user, returns user profile.
- `POST /login`
  - Body: `LoginRequest`
  - Behavior: verifies credentials, returns access token.
- `GET /me`
  - Auth required.
  - Returns current user.

### 5.2 Contacts Router (`/api/contacts`)
- `GET /`
  - Query: `skip`, `limit`, optional `search` by name.
  - Returns list of user-scoped contacts.
- `GET /{contact_id}`
- `POST /`
- `PATCH /{contact_id}`
- `DELETE /{contact_id}`

All contact routes are user-scoped (`contact.user_id == current_user.id`).

### 5.3 Deals Router (`/api/deals`)
- `GET /`
  - Query: `skip`, `limit`, optional `stage`, optional `status`.
- `GET /{deal_id}`
- `POST /`
- `PATCH /{deal_id}`
- `PATCH /{deal_id}/stage`
  - Body: `{ "stage": "..." }`
  - Auto-sets status to `won` for `closed_won`, `lost` for `closed_lost`.
- `DELETE /{deal_id}`

### 5.4 Activities Router (`/api/activities`)
- `GET /`
  - Query: `skip`, `limit`, optional `contact_id`, `deal_id`.
- `GET /{activity_id}`
- `POST /`
- `DELETE /{activity_id}`

### 5.5 Analytics Router (`/api/analytics`)
- `GET /summary`
  - Returns: contacts count, deals count, activities count, active pipeline value, won value.
- `GET /win-rate`
  - Returns stage distribution and win-rate percentage based on closed won/lost counts.
- `GET /forecast`
  - Returns weighted forecast from active deals using hardcoded stage weights.

### 5.6 AI Router (`/api/ai`)
- `GET /score/{contact_id}`
  - Builds feature vector from contact + activity counts.
  - Calls local model scorer.
- `POST /insights`
  - Returns placeholder static insights.

## 6. Domain Model Summary
- `User`: account owner and tenancy boundary.
- `Contact`: lead/customer record.
- `Deal`: opportunity tied to optional contact.
- `Activity`: timeline event tied to optional contact and optional deal.
- `PipelineStage`: user-specific stage metadata.

Detailed table schema is in `docs/DATABASE_SCHEMA_AND_ERD.md`.

## 7. Migrations
Files:
- `backend/alembic/env.py`
- `backend/alembic/versions/0001_initial.py`

`0001_initial.py` creates all 5 core tables and FK relationships.

## 8. Build and Run

### 8.1 Docker Compose
- From repo root: `docker compose up --build`

### 8.2 Backend Container Command
In `backend/Dockerfile` the container startup command is:
- `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`

## 9. Backend Known Gaps
- No refresh-token implementation, only access token.
- No pagination envelope on list endpoints.
- Pipeline stage CRUD router is not implemented, even though model exists.
- Redis/AWS settings are present but not actively integrated in runtime behavior.

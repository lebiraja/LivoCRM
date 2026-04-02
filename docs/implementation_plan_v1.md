# LivoCRM — Full-Stack Project Scaffold

Scaffold the entire LivoCRM project from an empty repo into a runnable full-stack application following the spec in [LivoCRM_Plan.md](file:///home/lebi/projects/livocrm/LivoCRM_Plan.md) and the AI integration guide in [Bedrock_guide.md](file:///home/lebi/projects/livocrm/Bedrock_guide.md).

## Proposed Changes

### Backend (FastAPI + SQLAlchemy + Alembic)

#### [NEW] [requirements.txt](file:///home/lebi/projects/livocrm/backend/requirements.txt)
All Python dependencies: FastAPI, uvicorn, SQLAlchemy, Alembic, Pydantic, passlib, python-jose, boto3, scikit-learn, pandas, numpy, faker, celery, redis, python-dotenv, httpx.

---

#### [NEW] [config.py](file:///home/lebi/projects/livocrm/backend/app/config.py)
Pydantic `BaseSettings` loading all env vars: DATABASE_URL, SECRET_KEY, JWT algorithm/expiry, AWS Bedrock model IDs, Redis URL.

#### [NEW] [database.py](file:///home/lebi/projects/livocrm/backend/app/database.py)
SQLAlchemy async engine, `SessionLocal` factory, `Base` declarative base, `get_db` dependency.

---

#### [NEW] SQLAlchemy Models (`backend/app/models/`)
- [user.py](file:///home/lebi/projects/livocrm/backend/app/models/user.py) — `User` (id, email, name, password, plan, created_at)
- [contact.py](file:///home/lebi/projects/livocrm/backend/app/models/contact.py) — `Contact` (id, user_id FK, name, email, phone, company, tags, lead_score, notes, timestamps)
- [deal.py](file:///home/lebi/projects/livocrm/backend/app/models/deal.py) — `Deal` (id, user_id FK, contact_id FK, title, value, stage, expected_close, status, timestamps)
- [activity.py](file:///home/lebi/projects/livocrm/backend/app/models/activity.py) — `Activity` (id, user_id FK, contact_id FK, deal_id FK, type, description, occurred_at)
- [pipeline.py](file:///home/lebi/projects/livocrm/backend/app/models/pipeline.py) — `PipelineStage` (id, user_id FK, name, position, created_at)

---

#### [NEW] Pydantic Schemas (`backend/app/schemas/`)
- [user.py](file:///home/lebi/projects/livocrm/backend/app/schemas/user.py) — UserCreate, UserResponse, UserLogin, Token
- [contact.py](file:///home/lebi/projects/livocrm/backend/app/schemas/contact.py) — ContactCreate, ContactUpdate, ContactResponse
- [deal.py](file:///home/lebi/projects/livocrm/backend/app/schemas/deal.py) — DealCreate, DealUpdate, DealResponse
- [activity.py](file:///home/lebi/projects/livocrm/backend/app/schemas/activity.py) — ActivityCreate, ActivityResponse
- [pipeline.py](file:///home/lebi/projects/livocrm/backend/app/schemas/pipeline.py) — PipelineStageCreate, PipelineStageResponse
- [analytics.py](file:///home/lebi/projects/livocrm/backend/app/schemas/analytics.py) — DashboardStats, PipelineStats, ForecastData

---

#### [NEW] Services (`backend/app/services/`)
- [auth_service.py](file:///home/lebi/projects/livocrm/backend/app/services/auth_service.py) — Password hashing (bcrypt), JWT creation/validation, `get_current_user` dependency
- [lead_scoring.py](file:///home/lebi/projects/livocrm/backend/app/services/lead_scoring.py) — Load ML model, compute features, predict lead score
- [ai_service.py](file:///home/lebi/projects/livocrm/backend/app/services/ai_service.py) — AWS Bedrock client (from guide), call summarize, next-action, lead scoring via LLM

---

#### [NEW] Routers (`backend/app/routers/`)
- [auth.py](file:///home/lebi/projects/livocrm/backend/app/routers/auth.py) — POST `/register`, POST `/login`, GET `/me`
- [contacts.py](file:///home/lebi/projects/livocrm/backend/app/routers/contacts.py) — Full CRUD + `/{id}/activities`
- [deals.py](file:///home/lebi/projects/livocrm/backend/app/routers/deals.py) — Full CRUD with stage updates
- [activities.py](file:///home/lebi/projects/livocrm/backend/app/routers/activities.py) — POST + GET recent
- [analytics.py](file:///home/lebi/projects/livocrm/backend/app/routers/analytics.py) — Dashboard stats, pipeline, forecast
- [ai.py](file:///home/lebi/projects/livocrm/backend/app/routers/ai.py) — Lead score, summarize, next-action

---

#### [NEW] [main.py](file:///home/lebi/projects/livocrm/backend/app/main.py)
FastAPI app with CORS middleware, all routers mounted under `/api/`, startup event for DB table creation.

#### [NEW] Alembic setup (`backend/alembic/`)
- `alembic.ini` pointing to DATABASE_URL
- `env.py` importing all models
- Initial migration

---

#### [NEW] ML Layer (`backend/ml/`)
- [generate_data.py](file:///home/lebi/projects/livocrm/backend/ml/generate_data.py) — Faker-based synthetic CRM data (500+ contacts)
- [train_scorer.py](file:///home/lebi/projects/livocrm/backend/ml/train_scorer.py) — Train RandomForest on synthetic features → save `model.pkl`

---

### Frontend (React + Vite + Tailwind + shadcn/ui)

#### [NEW] Vite + React + TypeScript project in `frontend/`
Initialize with `npm create vite@latest` and install: Tailwind CSS, shadcn/ui, React Router v6, TanStack Query, Zustand, Recharts, Framer Motion, Axios, `@hello-pangea/dnd` (successor to react-beautiful-dnd).

#### [NEW] API Client (`frontend/src/api/client.ts`)
Axios instance with base URL, JWT interceptor from localStorage.

#### [NEW] Zustand Stores (`frontend/src/store/`)
- `authStore.ts` — user, token, login/logout
- `contactStore.ts` — contacts list, selected, filters
- `dealStore.ts` — deals, pipeline view state

#### [NEW] Pages (`frontend/src/pages/`)
- `LoginPage.tsx`, `RegisterPage.tsx` — Auth forms
- `DashboardPage.tsx` — Stats cards + charts (Recharts)
- `ContactsPage.tsx` — Searchable/filterable table
- `ContactDetailPage.tsx` — Full profile + activity timeline
- `PipelinePage.tsx` — Kanban board
- `AnalyticsPage.tsx` — Charts + forecast
- `SettingsPage.tsx` — Profile + pipeline stage management

#### [NEW] Components (`frontend/src/components/`)
- `Layout.tsx` — Sidebar nav + top bar wrapper
- `KanbanBoard/` — Drag-and-drop column/card components
- `ContactTable/` — Data table with sort/filter
- `ActivityTimeline/` — Vertical timeline
- `LeadScoreBadge/` — Color-coded ring (red/yellow/green)
- `AIInsightCard/` — Floating suggestion card
- `DealCard/` — Compact deal info card
- `StatsCard/` — Dashboard metric card
- `ThemeToggle/` — Dark/light mode switch

#### [NEW] Router (`frontend/src/App.tsx`)
React Router v6 with `ProtectedRoute` wrapper checking auth state.

---

### Infrastructure & Config

#### [NEW] [docker-compose.yml](file:///home/lebi/projects/livocrm/docker-compose.yml)
Services: `postgres` (v15), `redis` (v7), `backend` (FastAPI, depends on postgres+redis), `frontend` (Vite dev server).

#### [NEW] [nginx/nginx.conf](file:///home/lebi/projects/livocrm/nginx/nginx.conf)
Reverse proxy: `/api/` → backend:8000, `/` → frontend:5173.

#### [NEW] [.env.example](file:///home/lebi/projects/livocrm/.env.example)
Template with all env vars (DB, JWT, AWS Bedrock, Redis).

#### [NEW] [.gitignore](file:///home/lebi/projects/livocrm/.gitignore)
Python + Node + Docker + env patterns.

#### [NEW] [README.md](file:///home/lebi/projects/livocrm/README.md)
Project overview, tech stack, setup instructions, folder structure.

---

## Verification Plan

### Automated Tests
1. **Backend import check** — run `cd /home/lebi/projects/livocrm/backend && python -c "from app.main import app; print('OK')"` to verify all modules load without errors
2. **Frontend build check** — run `cd /home/lebi/projects/livocrm/frontend && npm run build` to verify TypeScript compiles and Vite builds successfully

### Manual Verification
1. **File structure** — verify the folder structure matches [LivoCRM_Plan.md](file:///home/lebi/projects/livocrm/LivoCRM_Plan.md) Section 12
2. **Docker Compose** — run `docker-compose config` to validate the compose file syntax
3. **Start backend dev server** — `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload` → verify Swagger docs at `http://localhost:8000/docs`
4. **Start frontend dev server** — `cd frontend && npm install && npm run dev` → verify the app loads at `http://localhost:5173`

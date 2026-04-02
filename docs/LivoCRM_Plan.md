# LivoCRM — Live + Evolving CRM System
### Project Plan · IA3 MVP → SaaS Product Roadmap

> **LivoCRM** is a lightweight, AI-augmented Customer Relationship Management system built as a SaaS product. The name reflects its core philosophy — it is *live* (real-time, always in sync) and *evolving* (learns, adapts, and grows with the business using it). Designed first as an IA3 academic MVP, with a clear upgrade path to a production-grade SaaS.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [Target Users](#3-target-users)
4. [Core Features — IA3 MVP](#4-core-features--ia3-mvp)
5. [Extended Features — SaaS Product](#5-extended-features--saas-product)
6. [Tech Stack](#6-tech-stack)
7. [System Architecture](#7-system-architecture)
8. [Database Schema](#8-database-schema)
9. [API Design](#9-api-design)
10. [Frontend Design Plan](#10-frontend-design-plan)
11. [AI/ML Integration](#11-aiml-integration)
12. [Project Folder Structure](#12-project-folder-structure)
13. [Development Phases](#13-development-phases)
14. [IA3 Submission Scope](#14-ia3-submission-scope)
15. [SaaS Business Model](#15-saas-business-model)
16. [Future Roadmap](#16-future-roadmap)
17. [Team Roles (If Applicable)](#17-team-roles-if-applicable)

---

## 1. Project Overview

| Field | Details |
|---|---|
| **Project Name** | LivoCRM |
| **Full Form** | Live + Evolving CRM |
| **Type** | Web-based SaaS Application |
| **Domain** | Business Intelligence · CRM · AI/ML |
| **Current Stage** | IA3 MVP |
| **Target Stage** | Production SaaS |
| **Stack** | React + FastAPI + PostgreSQL + AI Layer |

**What is LivoCRM?**

LivoCRM is a smart CRM (Customer Relationship Management) platform that goes beyond storing contacts and deals. It actively learns from your sales data, predicts which leads are most likely to convert, surfaces actionable insights, and evolves its recommendations over time. Unlike traditional CRMs (Salesforce, HubSpot) that require heavy setup and enterprise pricing, LivoCRM is designed to be plug-and-play for small teams, startups, and freelancers — while scaling to larger organizations via SaaS tiers.

---

## 2. Problem Statement

Traditional CRMs suffer from:

- **Data entry fatigue** — Sales reps spend hours logging calls, emails, and meetings manually.
- **Static pipelines** — No intelligence; just a digital sticky-note board.
- **High pricing** — Salesforce/HubSpot cost hundreds per seat/month; inaccessible for small teams.
- **No learning loop** — CRMs don't get smarter over time; they just store more data.
- **Poor mobile/voice UX** — Built for desktop power users, not field reps.

**LivoCRM solves this by:**

- Auto-capturing interaction data (emails, calls, notes) with minimal manual entry.
- Using AI to score leads, predict churn, and surface next-best actions.
- Offering a freemium SaaS model that starts free and scales affordably.
- Being lightweight enough to work beautifully on mobile.

---

## 3. Target Users

| User Segment | Description |
|---|---|
| **Freelancers** | Manage clients, proposals, invoices, and follow-ups in one place |
| **Startups (1–20 people)** | Lightweight sales pipeline without enterprise complexity |
| **SMBs** | Small-medium businesses needing a team-level CRM with reporting |
| **Student Projects / Incubation Cells** | Academic and early-stage teams managing leads and partnerships |
| **Agency Owners** | Track client projects, retention, and deal progress |

> **Primary Persona for IA3:** A startup or small sales team of 2–5 people managing 50–200 leads across a sales pipeline.

---

## 4. Core Features — IA3 MVP

These are the features that will be built and demonstrated for the IA3 submission.

### 4.1 Authentication & Multi-Tenancy (Basic)

- User registration and login (JWT-based auth)
- Each user has their own isolated workspace (tenant)
- Password hashing with bcrypt
- Protected API routes

### 4.2 Contact Management

- Add, edit, delete contacts (name, email, phone, company, tags)
- View all contacts in a searchable, filterable table
- Assign contacts to pipeline stages
- Add notes to contacts (timestamped)
- Contact activity log (when added, last updated, last contacted)

### 4.3 Deal / Pipeline Management

- Kanban-style drag-and-drop pipeline board
- Default stages: `Lead → Qualified → Proposal → Negotiation → Won → Lost`
- Custom stage creation (user-defined)
- Deal cards with: value, contact linked, expected close date, assigned rep
- Move deals across stages with timestamp tracking

### 4.4 Activity Tracking

- Log activities manually: Call, Email, Meeting, Note
- Each activity linked to a contact or deal
- Timeline view per contact showing all interactions

### 4.5 Basic Dashboard & Analytics

- Total contacts, deals, value in pipeline
- Win rate (Won / Total closed)
- Deals by stage (bar chart)
- Revenue forecast (sum of open deal values)
- Recent activity feed

### 4.6 AI Lead Scoring (Core AI Feature)

- Rule-based + ML hybrid lead scoring (0–100 score)
- Scoring factors: recency of contact, number of interactions, deal stage, deal value
- Displayed as a badge on each contact/deal card
- Simple linear regression or random forest trained on synthetic data for IA3

### 4.7 Search & Filters

- Global search across contacts and deals
- Filter by stage, tags, assigned user, date range, lead score

### 4.8 Responsive UI

- Works on desktop and mobile
- Clean, modern dashboard layout
- Dark/light mode toggle

---

## 5. Extended Features — SaaS Product

These will be added after IA3 as the product evolves.

### 5.1 Email Integration

- Connect Gmail / Outlook via OAuth
- Auto-log emails to the relevant contact's timeline
- AI-generated email reply suggestions (via Claude API)

### 5.2 AI Conversation Summaries

- Paste or upload call transcripts
- AI summarizes key points, action items, and sentiment
- Stored under the contact's activity log

### 5.3 Churn Prediction

- ML model trained on engagement drop-off patterns
- Alert when a previously active customer goes quiet
- Recommended follow-up action generated by AI

### 5.4 Smart Reminders & Follow-Up Engine

- AI detects when a deal has been stale for too long
- Sends automated reminder to assigned rep
- Suggests follow-up message draft

### 5.5 Team Collaboration

- Multiple users per organization (team workspace)
- Role-based access: Admin, Sales Rep, Viewer
- Deal assignment and internal notes/comments

### 5.6 Integrations

- Zapier / Make.com webhooks
- Slack notifications for deal stage changes
- Calendar sync (Google Calendar)
- WhatsApp Business API for follow-up messages

### 5.7 Reports & Exports

- Downloadable CSV/PDF reports
- Sales performance per rep
- Custom report builder (filter → group → chart)

### 5.8 Custom Fields

- Users can add custom fields to contacts and deals
- Dynamic form builder for intake forms

### 5.9 Mobile App (React Native)

- Voice-first interaction: "Log a call with Ravi, he's interested"
- Push notifications for reminders
- Quick-add contact via camera (business card scan using OCR)

### 5.10 API & Webhooks for Developers

- Public REST API for CRM data
- Webhook triggers on deal stage changes, new contacts, etc.
- Developer dashboard with API key management

---

## 6. Tech Stack

### Frontend

| Technology | Purpose |
|---|---|
| **React 18** | UI framework |
| **Vite** | Build tool (fast HMR) |
| **Tailwind CSS** | Styling |
| **shadcn/ui** | Component library |
| **React Query (TanStack)** | Server state management |
| **Zustand** | Client state management |
| **React Beautiful DnD** | Drag-and-drop Kanban board |
| **Recharts** | Dashboard charts |
| **React Router v6** | Client-side routing |
| **Framer Motion** | UI animations |

### Backend

| Technology | Purpose |
|---|---|
| **Python 3.11+** | Backend language |
| **FastAPI** | REST API framework |
| **SQLAlchemy** | ORM for database access |
| **Alembic** | Database migrations |
| **Pydantic v2** | Data validation and serialization |
| **python-jose** | JWT token handling |
| **passlib + bcrypt** | Password hashing |
| **Celery + Redis** | Async task queue (for AI jobs, reminders) |

### Database

| Technology | Purpose |
|---|---|
| **PostgreSQL 15** | Primary relational database |
| **Redis** | Caching + Celery broker |

### AI / ML Layer

| Technology | Purpose |
|---|---|
| **scikit-learn** | Lead scoring model (Random Forest) |
| **pandas / numpy** | Data processing |
| **Claude API (Anthropic)** | Email drafts, call summaries, smart suggestions |
| **sentence-transformers** | Contact deduplication via semantic similarity |

### DevOps & Infrastructure

| Technology | Purpose |
|---|---|
| **Docker + Docker Compose** | Local development environment |
| **Nginx** | Reverse proxy |
| **GitHub Actions** | CI/CD pipeline |
| **Render / Railway** | Backend hosting (MVP) |
| **Vercel** | Frontend hosting |
| **Supabase** | Managed PostgreSQL (optional for SaaS) |

---

## 7. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      CLIENT LAYER                       │
│         React SPA (Vite + Tailwind + shadcn/ui)         │
│   Dashboard │ Pipeline │ Contacts │ Analytics │ Settings │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS / REST API
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    API GATEWAY LAYER                    │
│              FastAPI (Python 3.11+)                     │
│  Auth │ Contacts │ Deals │ Activities │ AI Endpoints    │
└──────────┬──────────────────────────┬───────────────────┘
           │                          │
           ▼                          ▼
┌──────────────────┐        ┌─────────────────────────────┐
│   PostgreSQL DB  │        │        AI / ML Layer         │
│  (Primary store) │        │  Lead Scoring │ Summaries    │
│                  │        │  Claude API   │ Churn Model  │
└──────────────────┘        └─────────────────────────────┘
           │
           ▼
┌──────────────────┐
│   Redis Cache    │
│  + Celery Queue  │
│  (Async tasks)   │
└──────────────────┘
```

### Data Flow — Lead Scoring

```
New Contact Created
        │
        ▼
Interaction Events Logged (calls, emails, notes)
        │
        ▼
Feature Extraction (recency, frequency, deal value, stage)
        │
        ▼
ML Model (Random Forest / Rule Engine)
        │
        ▼
Lead Score (0–100) stored in DB
        │
        ▼
Score Badge displayed on Contact / Deal Card
```

---

## 8. Database Schema

### Users Table
```sql
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE NOT NULL,
    name        VARCHAR(255) NOT NULL,
    password    VARCHAR(255) NOT NULL,      -- bcrypt hashed
    plan        VARCHAR(50) DEFAULT 'free', -- free | pro | enterprise
    created_at  TIMESTAMP DEFAULT NOW()
);
```

### Contacts Table
```sql
CREATE TABLE contacts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    name        VARCHAR(255) NOT NULL,
    email       VARCHAR(255),
    phone       VARCHAR(50),
    company     VARCHAR(255),
    tags        TEXT[],                     -- array of tags
    lead_score  INTEGER DEFAULT 0,          -- 0–100
    notes       TEXT,
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);
```

### Deals Table
```sql
CREATE TABLE deals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    contact_id      UUID REFERENCES contacts(id),
    title           VARCHAR(255) NOT NULL,
    value           NUMERIC(12, 2) DEFAULT 0,
    stage           VARCHAR(100) DEFAULT 'Lead',
    expected_close  DATE,
    status          VARCHAR(50) DEFAULT 'open',  -- open | won | lost
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);
```

### Activities Table
```sql
CREATE TABLE activities (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    contact_id  UUID REFERENCES contacts(id),
    deal_id     UUID REFERENCES deals(id),
    type        VARCHAR(50) NOT NULL,   -- call | email | meeting | note
    description TEXT,
    occurred_at TIMESTAMP DEFAULT NOW()
);
```

### Pipeline Stages Table
```sql
CREATE TABLE pipeline_stages (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    name        VARCHAR(100) NOT NULL,
    position    INTEGER NOT NULL,        -- order of stage in pipeline
    created_at  TIMESTAMP DEFAULT NOW()
);
```

---

## 9. API Design

### Auth Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, returns JWT |
| GET | `/api/auth/me` | Get current user profile |

### Contact Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/contacts` | List all contacts (with filters, pagination) |
| POST | `/api/contacts` | Create new contact |
| GET | `/api/contacts/{id}` | Get single contact |
| PUT | `/api/contacts/{id}` | Update contact |
| DELETE | `/api/contacts/{id}` | Delete contact |
| GET | `/api/contacts/{id}/activities` | Get all activities for a contact |

### Deal Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/deals` | List all deals |
| POST | `/api/deals` | Create new deal |
| GET | `/api/deals/{id}` | Get single deal |
| PUT | `/api/deals/{id}` | Update deal (incl. stage change) |
| DELETE | `/api/deals/{id}` | Delete deal |

### Activity Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/activities` | Log a new activity |
| GET | `/api/activities` | Get all recent activities |

### AI Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/ai/lead-score/{contact_id}` | Get AI lead score for a contact |
| POST | `/api/ai/summarize` | Summarize a call transcript |
| GET | `/api/ai/next-action/{deal_id}` | Get AI-suggested next action for a deal |

### Analytics Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/analytics/dashboard` | Summary stats (contacts, deals, win rate) |
| GET | `/api/analytics/pipeline` | Deals grouped by stage |
| GET | `/api/analytics/forecast` | Revenue forecast from open deals |

---

## 10. Frontend Design Plan

### Pages

| Page | Route | Description |
|---|---|---|
| Login / Register | `/login`, `/register` | Auth pages |
| Dashboard | `/` | Overview stats, recent activity, charts |
| Contacts | `/contacts` | Table view of all contacts |
| Contact Detail | `/contacts/:id` | Full profile, activity timeline |
| Pipeline | `/pipeline` | Kanban drag-and-drop deal board |
| Deal Detail | `/deals/:id` | Full deal info and linked contact |
| Analytics | `/analytics` | Charts, reports, forecast |
| Settings | `/settings` | Profile, pipeline stages, integrations |

### Key UI Components

- **Kanban Board** — drag-and-drop cards across pipeline stages
- **Activity Timeline** — vertical timeline per contact with type icons (📞 📧 📝)
- **Lead Score Badge** — color-coded ring: 0–40 red, 41–70 yellow, 71–100 green
- **AI Insight Cards** — floating suggestion cards ("Follow up with Ravi — 7 days no contact")
- **Deal Card** — compact card showing value, contact, expected close, score
- **Global Search** — Cmd+K command palette for instant search

### Design Language

- **Theme:** Dark-first with optional light mode
- **Colors:** Deep navy `#0F172A` background, electric blue `#3B82F6` primary, emerald `#10B981` for won deals, red `#EF4444` for lost
- **Font:** `Geist Mono` for metrics/scores, `Inter` for body text
- **Interactions:** Smooth drag transitions, toast notifications, loading skeletons

---

## 11. AI/ML Integration

### Lead Scoring Model (IA3 Scope)

**Features used for scoring:**
- Days since contact was created
- Number of activities logged
- Current pipeline stage (mapped to numeric)
- Deal value (if any deal linked)
- Days since last activity

**Model:** Random Forest Classifier (trained on synthetic/sample CRM data)

**Output:** Score 0–100, stored in contacts table, updated on each new activity

**Training Data (for IA3):** Synthetically generated using `faker` library — 500+ fake contacts with varied activity patterns, some labeled "converted" and "churned"

```python
# Simplified scoring logic
features = [
    days_since_created,
    num_activities,
    stage_index,         # Lead=0, Qualified=1, ..., Won=5
    deal_value_log,      # log(deal_value + 1) for normalization
    days_since_last_act
]
score = model.predict_proba([features])[0][1] * 100  # probability of conversion
```

### AI Suggestions (Claude API — SaaS Phase)

For the SaaS product, Claude API will power:
- **Email draft generation:** "Write a follow-up email for Ravi after our last call"
- **Call summary:** Paste transcript → get bullet points + action items
- **Next best action:** Based on deal stage and contact history, suggest what to do next
- **Sentiment analysis:** Detect if a contact is cooling off from their activity patterns

---

## 12. Project Folder Structure

```
livocrm/
│
├── frontend/                       # React app
│   ├── src/
│   │   ├── components/             # Reusable UI components
│   │   │   ├── ui/                 # shadcn/ui base components
│   │   │   ├── KanbanBoard/
│   │   │   ├── ContactTable/
│   │   │   ├── ActivityTimeline/
│   │   │   ├── LeadScoreBadge/
│   │   │   └── AIInsightCard/
│   │   ├── pages/                  # Route-level pages
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Contacts.jsx
│   │   │   ├── ContactDetail.jsx
│   │   │   ├── Pipeline.jsx
│   │   │   ├── Analytics.jsx
│   │   │   └── Settings.jsx
│   │   ├── hooks/                  # Custom React hooks
│   │   ├── store/                  # Zustand state stores
│   │   ├── api/                    # API client (axios)
│   │   └── utils/
│   ├── index.html
│   └── vite.config.js
│
├── backend/                        # FastAPI app
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── config.py               # Settings (env vars)
│   │   ├── database.py             # DB session setup
│   │   ├── models/                 # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── contact.py
│   │   │   ├── deal.py
│   │   │   ├── activity.py
│   │   │   └── pipeline.py
│   │   ├── schemas/                # Pydantic schemas
│   │   ├── routers/                # FastAPI routers
│   │   │   ├── auth.py
│   │   │   ├── contacts.py
│   │   │   ├── deals.py
│   │   │   ├── activities.py
│   │   │   ├── analytics.py
│   │   │   └── ai.py
│   │   ├── services/               # Business logic
│   │   │   ├── auth_service.py
│   │   │   ├── lead_scoring.py
│   │   │   └── ai_service.py
│   │   └── middleware/
│   ├── alembic/                    # DB migrations
│   ├── ml/                         # ML model training & inference
│   │   ├── train_scorer.py
│   │   ├── generate_data.py
│   │   └── model.pkl
│   └── requirements.txt
│
├── docker-compose.yml              # Full stack local dev
├── nginx/
│   └── nginx.conf
├── .env.example
├── README.md
└── PLAN.md                         # This file
```

---

## 13. Development Phases

### Phase 1 — Foundation (Week 1)
- [ ] Set up GitHub repo and project board
- [ ] Initialize React (Vite) + FastAPI project
- [ ] Docker Compose: PostgreSQL + Redis + Backend + Frontend
- [ ] Auth system: register, login, JWT middleware
- [ ] User model + contacts model in DB
- [ ] Alembic migrations working

### Phase 2 — Core CRM (Week 2)
- [ ] Contact CRUD API + frontend table
- [ ] Deal CRUD API + Kanban board UI
- [ ] Activity logging API + timeline UI
- [ ] Pipeline stage management (default + custom)
- [ ] Contact detail page with activity feed

### Phase 3 — AI Feature + Dashboard (Week 3)
- [ ] Synthetic training data generator (`generate_data.py`)
- [ ] Train Random Forest lead scoring model
- [ ] Lead scoring endpoint + badge on UI
- [ ] Dashboard page: stats cards + charts (Recharts)
- [ ] Analytics: pipeline chart, revenue forecast

### Phase 4 — Polish + IA3 Submission (Week 4)
- [ ] Search and filter across contacts and deals
- [ ] Dark/light mode toggle
- [ ] Mobile responsiveness
- [ ] Demo data seeder (for evaluation)
- [ ] Documentation: README + API docs (Swagger auto-generated)
- [ ] Deploy: Vercel (frontend) + Render (backend)
- [ ] Record demo video

---

## 14. IA3 Submission Scope

The following is the exact scope that will be demonstrated for the IA3 assessment.

### Must-Have (M1)
- [x] User authentication (register/login/JWT)
- [x] Contact management (CRUD)
- [x] Deal pipeline (Kanban board)
- [x] Activity logging and timeline
- [x] AI Lead Scoring (ML model)
- [x] Dashboard with stats and one chart

### Should-Have (M2)
- [x] Search and filter
- [x] Custom pipeline stages
- [x] Deal value and revenue forecast
- [x] Mobile responsive layout

### Nice-to-Have (M3)
- [ ] Dark mode
- [ ] Claude API for next-best-action suggestion
- [ ] Export contacts to CSV

### Deliverables for IA3

| Item | Description |
|---|---|
| **GitHub Repo** | Full source code, well-documented |
| **Live Demo URL** | Deployed on Vercel + Render |
| **Demo Video** | 3–5 min walkthrough of all features |
| **Project Report** | Architecture, AI model explanation, challenges |
| **Swagger Docs** | Auto-generated API documentation at `/docs` |

---

## 15. SaaS Business Model

### Pricing Tiers (Post-MVP)

| Plan | Price | Limits |
|---|---|---|
| **Free** | ₹0 / $0 | 1 user, 100 contacts, 10 deals, basic features |
| **Starter** | ₹499 / $9/mo | 3 users, 1000 contacts, unlimited deals, AI scoring |
| **Pro** | ₹1499 / $29/mo | 10 users, unlimited contacts, email integration, reports |
| **Enterprise** | Custom | Unlimited, SSO, dedicated support, custom integrations |

### Revenue Streams

- **Subscription revenue** — primary SaaS model
- **API access** — pay-per-call for AI endpoints
- **Integration marketplace** — premium connectors (WhatsApp, Shopify)
- **White-label licensing** — agencies can resell LivoCRM under their brand

### Growth Strategy

- Launch on **Product Hunt** and **Hacker News (Show HN)**
- **Indie hacker communities** (small teams that avoid Salesforce)
- **Incubation cells and startup hubs** — academic and early-stage teams
- SEO: "free CRM for startups India", "simple CRM for freelancers"
- Free tier as acquisition channel → upsell with AI features

---

## 16. Future Roadmap

| Version | Feature |
|---|---|
| **v1.0** | IA3 MVP (all Phase 1–4 features) |
| **v1.5** | Email integration (Gmail OAuth), team workspaces |
| **v2.0** | Claude AI for summaries, email drafts, next-best-action |
| **v2.5** | Mobile app (React Native), voice logging |
| **v3.0** | Custom report builder, Zapier integration |
| **v3.5** | Churn prediction model, smart reminders |
| **v4.0** | Marketplace for integrations, white-label tier |
| **v5.0** | Vertical CRM versions (Real Estate LivoCRM, Agency LivoCRM) |

---

## 17. Team Roles (If Applicable)

| Role | Responsibilities |
|---|---|
| **Technical Lead** | Architecture, AI/ML layer, code review, deployment |
| **Backend Dev** | FastAPI routes, DB models, auth, services |
| **Frontend Dev** | React components, Kanban board, dashboard |
| **ML Engineer** | Lead scoring model, training pipeline, AI endpoints |
| **UI/UX Designer** | Design system, Figma mockups, component library |

> For solo development: all roles collapse to one person. Use GitHub Issues to track tasks per role.

---

## Notes & Philosophy

> **"A CRM should feel like a smart co-pilot, not a data entry chore."**

LivoCRM is built on three guiding principles:

1. **Minimum friction** — every interaction should take fewer clicks than a competitor.
2. **Intelligence by default** — AI features aren't add-ons; they're baked into the core experience.
3. **Live and evolving** — the system learns from usage, improves lead scores, refines suggestions, and grows with the team using it.

The IA3 MVP is not a toy. It is the first working version of a real product. Every architectural decision made here will carry forward to the SaaS version without a full rewrite. Build it right from day one.

---

*LivoCRM — Built for IA3. Designed for the real world.*
*Project by Lebi · URK24AI1005 · Karunya Institute of Technology and Sciences · 2024–2028*

# 09 - IA3 Rubric Mapping

Purpose: map each IA3 rubric (6 x 5 marks = 30) to the evidence LivoCRM must show, the feature/doc/demo that supplies it, and the gaps; plus viva questions, a demo script, deliverables and a differentiation note.
Date: 2026-10-26 | Status: draft for Lebi to check against the signed rubric sheet (level descriptors are not in the repo) | Author: research-agent
Feature IDs (F1-F19) refer to `08-feature-research.md` section 2.2. Current-state facts come from `01-code-audit.md` and `06-ui-audit-and-research.md`.

## 0. Ground rules

- The signed rubric names Node.js + MongoDB and HTML5/CSS3/Bootstrap/JS + React/Angular/jQuery. Lebi confirmed with faculty that the existing stack is accepted. **Gap:** get that acceptance in writing (email or a signed line on the rubric sheet) and put it in the report appendix.
- Put a "stack equivalence" slide and report table up front so the examiner never has to ask:

| Rubric names | LivoCRM uses | Equivalence argument |
|---|---|---|
| Node.js (Express) | FastAPI on Uvicorn (Python 3.12, ASGI) | Both are async, event-loop servers exposing REST + WebSocket; FastAPI adds Pydantic validation and auto OpenAPI docs at `/docs` |
| MongoDB | PostgreSQL 16 + SQLAlchemy 2 async + Alembic | Relational integrity (FKs, CHECKs, unique) for appointments and money; JSON column for flexible `tags` covers the document-store use case |
| HTML5 / CSS3 / Bootstrap / JS | React 19 + TypeScript + Tailwind CSS v4 + shadcn/ui (Radix) | Semantic HTML5 rendered by React; CSS3 through Tailwind utilities; shadcn plays Bootstrap's component-library role; TypeScript is typed JavaScript |
| React / Angular / jQuery | React 19 + Vite + React Router + Zustand | React is named in the rubric |
| (implicit) deployment | Docker Compose: db, redis, backend, frontend, nginx, pgadmin; Nginx single entry on :3500 | Reproducible one-command run |

- The MongoDB certificate is a separate 10-mark item, already handled by Lebi; not covered here.

## 1. Rubric -> evidence map

| # | Rubric (5 marks) | Evidence the examiner must see | Supplied by | Current state | Gaps to close |
|---|---|---|---|---|---|
| R1 | Front-end design | Consistent visual system; responsive (phone + laptop); clear navigation; forms with validation and errors; loading/empty/error states; accessibility basics; one distinctive screen | `07-ui-redesign-plan.md`; F15 Tamil/English UI; F3 SLA chips; F6 recovered-revenue card; F16 appointment day view; F8 PWA install | Existing React/shadcn UI; no i18n, no Tamil font, layouts assume short English labels (`06` I1-I3); dashboard WS unused | Tamil font + locale switch on main screens; mobile pass on appointments and inbox; empty/error states; before/after screenshots for the report |
| R2 | Back-end integration | REST API with auth; DB schema + migrations; validation; real-time channel; external service integration; background job; error handling | FastAPI routers + Alembic 0001-0007 (existing); F11 Groq with strict JSON and fallback; F18 outbox worker; F14 inbound webhook; F13 audit log; `sms_service_tool` adapter | 35 HTTP + 2 WS routes; JWT auth; Bedrock sync calls block the event loop (`routers/chat.py:203`); frontend/backend contract mismatches noted in `docs/ARCHITECTURE_OVERVIEW.md` section 8 | Fix contract mismatches; Groq async client; new tables (appointments, messages, consents, audit_log, leads) with migrations; API.md updated |
| R3 | Functionality | End-to-end user stories work live without hand-waving | F16 appointments, F18 reminders, F14 lead inbox, F5 no-show recovery, F12 CSV import, F10 demo seed, existing contacts/deals/pipeline/chat | CRUD + pipeline + AI chat exist; no clinic objects; no tests (`01` Tests section) | Phases A-C of `08` 2.3; pytest for appointment/outbox/recovery; Playwright happy path; demo seed reproducible |
| R4 | Presentation | Clear problem -> solution -> architecture -> live demo -> results -> limits story within time; confident Q&A | Section 3 demo script; section 2 viva bank; PPT outline in section 4 | Not started | Rehearse twice with a timer; record a backup video; print the architecture diagram |
| R5 | Innovation | Something original and current, explained honestly | F4 Tamil/Tanglish copilot (Groq gpt-oss-120b, strict schema); F7 explainable lead score; F3 SLA timers with live push; F10 simulation clock; F6 recovered-revenue ledger; F9 Tamil voice notes (Whisper) | AI chat that creates CRM records already exists (good base); lead score is unexplained and fed a constant (`routers/ai.py` omits `days_since_last_activity`) | Build at least F4 + F7 + F3; measure Tamil quality on a small eval set and quote the real number |
| R6 | Documentation | Report with problem, requirements, architecture, DB design, API, UI, testing, results, limits, references; README to run it; API docs; diagrams | `docs/plan/01-09`; `docs/architecture.md`, `docs/API.md`, `docs/docker.md` (keep in sync via docs-keeper); OpenAPI at `/docs`; this file | Many overlapping legacy docs (`docs/` has 20 files, several stale); DBMS report exists and must not be recycled (section 6) | One clean IA3 report; prune or archive stale docs; ER diagram updated with new tables; test evidence screenshots |

### 1.1 Evidence checklist (tick before submission)

- [ ] R1: screenshots at 375 px and 1440 px for dashboard, inbox, appointments, contact detail; Tamil and English versions of one screen
- [ ] R1: Lighthouse accessibility score screenshot for the dashboard (report the real number)
- [ ] R2: updated ER diagram including appointments, messages, consents, leads, audit_log
- [ ] R2: OpenAPI `/docs` screenshot; `docs/API.md` lists new endpoints
- [ ] R2: sequence diagram: missed call -> webhook -> lead -> SLA timer -> reply -> appointment -> reminder -> no-show -> recovery
- [ ] R2: proof of fallback: chat still answers with `AI_PROVIDER=off` (deterministic replies)
- [ ] R3: `docker compose up` from a clean clone + demo seed works on a second machine
- [ ] R3: pytest and vitest run output in the report (counts, not claims)
- [ ] R4: PPT, backup demo video (MP4, offline), printed one-page architecture
- [ ] R5: Tamil eval table (n items, pass rate, examples of failures)
- [ ] R5: lead-score explanation shown for one hot and one cold contact
- [ ] R6: report with references (Groq docs, Meta pricing, DPDP Rules, TRAI) and access dates
- [ ] Faculty stack acceptance in writing (appendix)

## 2. Viva question bank (25)

| # | Question | Short answer (check against the final code) |
|---|---|---|
| 1 | The rubric says Node + MongoDB. Why FastAPI + PostgreSQL? | Faculty approved. Appointments, payments-like fees and consent are relational with integrity rules (FKs, CHECKs). FastAPI is async like Node and gives typed validation and OpenAPI docs for free. |
| 2 | How does a request flow from the browser to the database? | Browser -> Nginx :3500 -> `/api/*` proxied to the FastAPI container -> dependency injects an async SQLAlchemy session -> asyncpg -> PostgreSQL. Static React build is served by the frontend container behind the same Nginx. |
| 3 | How is authentication done? | Register/login return an HS256 JWT signed with `SECRET_KEY` (python-jose), 30-minute expiry; passwords hashed with bcrypt. `get_current_user` decodes the bearer token and loads the user. |
| 4 | Where is the token stored and what is the risk? | In `localStorage` (axios interceptor adds the header). Risk: XSS can read it. Mitigations: no `dangerouslySetInnerHTML`, CSP in Nginx, short expiry; httpOnly cookie is the stronger option. |
| 5 | How do you stop one user reading another's data? | Every query filters by `user_id == current_user.id`; ownership is checked before linking a deal/appointment to a contact. With RBAC, a clinic/workspace id plus role check. |
| 6 | Why UUID primary keys? | Not guessable in URLs, safe to generate anywhere, no ID enumeration across tenants. Cost: larger indexes. |
| 7 | What do Alembic migrations give you? | Versioned, repeatable schema changes (0001-0007 today); the backend runs `alembic upgrade head` on start, so every environment converges to the same schema. |
| 8 | What constraints protect data integrity? | FKs with `CASCADE`/`SET NULL`, CHECK constraints on stage/status/source/type, unique constraints, indexes on foreign keys. |
| 9 | What is Redis used for? | Chat session context (state machine, collected fields, last messages) with a 1-hour TTL, so multi-turn AI flows survive between requests. |
| 10 | How does real-time update work? | WebSockets at `/ws/...`; Nginx forwards the Upgrade headers. The backend pushes events (new lead, SLA breach, reminder sent) to the dashboard. |
| 11 | How does the reminder scheduler avoid sending twice? | Outbox rows with a unique idempotency key (appointment + rule); the worker claims due rows with `SELECT ... FOR UPDATE SKIP LOCKED` and marks them sent in the same transaction. |
| 12 | Why Groq, and which models? | OpenAI-compatible API, very fast inference, cheap open-weight models. `openai/gpt-oss-20b` for intent + extraction, `openai/gpt-oss-120b` for Tamil/English message drafts, `whisper-large-v3` for voice notes. |
| 13 | How do you make sure the LLM returns valid JSON? | Groq strict structured outputs (`json_schema`, `strict: true`): constrained decoding against a schema where all fields are required (nullable if optional) and `additionalProperties: false`. Pydantic validates again server-side. |
| 14 | What happens if Groq is down or rate-limited? | SDK retries 429/5xx twice with backoff, honour `retry-after`, then fall back to the other model (separate rate-limit bucket), then deterministic rules/templates. The CRM never depends on AI to save data. |
| 15 | Is patient data safe with an AI provider? | Only the minimum is sent (first name, time, clinic); no notes or diagnosis. Groq Zero Data Retention enabled; data processed in the US. Under DPDP the clinic is the Data Fiduciary and we are a Processor. |
| 16 | What does DPDP require of this app? | Notice and consent per purpose, ability to withdraw (opt-out), security safeguards, breach reporting, deletion when purpose ends. Main obligations from about 13 May 2027 (a shorter timeline was proposed, not notified as of 26 Oct 2026). |
| 17 | Why not send real WhatsApp messages? | The Cloud API needs Meta business verification and approved templates, and since 1 Oct 2026 in-window service and utility messages are billed. The outbox is channel-agnostic: simulated, wa.me links and an Android SMS gateway now; the WhatsApp API is one more adapter. |
| 18 | Is the SMS gateway legal for clinics? | For a demo to consenting test numbers, yes. Bulk commercial SMS needs DLT registration under TRAI rules; unregistered 10-digit senders can be reported and disconnected, so production would use a DLT-registered provider. |
| 19 | How is the lead score computed? | RandomForest (100 trees) on 7 features: has company/phone/email, tag count, notes length, activity count, days since last activity. Trained on synthetic data whose labels come from a weighted formula, so the explanation shows the contributing factors. Real clinic data would retrain it. |
| 20 | How is "revenue recovered" calculated? | Sum of the consult fee for appointments completed after a reminder or recovery message, e.g. a no-show rebooked within N days or a missed call converted. It is attributed, not proven causal; the rule is shown on screen. |
| 21 | How is the SLA timer calculated? | `first_response_at - received_at` per lead, computed on the server; the UI only renders the countdown. Dashboard shows p50/p90 response time. |
| 22 | How does Tamil support work? | UI strings in JSON catalogues per locale with a Tamil font (Noto Sans Tamil), `en-IN` number formatting, and a per-contact preferred language for outbound messages. AI drafts in Tamil, English or Tanglish are always reviewed by staff. |
| 23 | How did you test it? | pytest + pytest-asyncio with httpx for API and scheduler logic, LLM calls mocked; vitest + Testing Library for components; Playwright for the booking-to-reminder path. Report real pass counts. |
| 24 | How is it deployed and configured? | Docker Compose with healthchecks on Postgres and Redis; services talk over the `livocrm` bridge network by name; secrets via `env_file: .env` (never committed); Nginx is the only app entry (:3500). Postgres (:5435) and pgAdmin (:5050) are published for development only and should be closed in production. |
| 25 | What are the limitations, and what's next? | Single-process WebSocket registry; simulated channels; Tamil AI quality measured on a small set; no real clinic pilot yet. Next: WhatsApp API via a BSP, a telephony missed-call webhook, and a 2-3 clinic pilot in Coimbatore. |

Extra traps to prepare for: "show me where X is in the code" (keep a file map slide), "what happens if two staff book the same slot" (unique/exclusion constraint), "why Zustand over Redux" (small, no boilerplate), "difference between `async def` and threads in FastAPI".

## 3. Demo script (target 9 minutes, hard stop 10)

Setup before the viva: fresh `docker compose up`, demo seed loaded, `AI_PROVIDER=groq` with key checked, Developer tier or a quota check done in the morning, browser zoom 110%, second browser logged in as front desk, Android phone with the SMS gateway on the same network, backup video open in another tab, Wi-Fi + phone hotspot.

| Time | Step | What to show | Rubric |
|---|---|---|---|
| 0:00-0:45 | Problem | One slide: TN clinic misses calls, patients no-show, no one follows up; "never miss a lead, recover the no-show, show the ₹" | R4 |
| 0:45-1:30 | Architecture | Diagram: React -> Nginx -> FastAPI -> Postgres/Redis; worker; Groq; channel adapters. Say the stack-equivalence line once | R2, R4 |
| 1:30-2:30 | Lead capture + SLA | Click "simulate missed call": lead appears live in the inbox (WebSocket), red SLA timer starts; reply, timer stops, response time recorded | R3, R5 |
| 2:30-3:45 | AI chat booking | Type in Tanglish: "Kavitha ku naalaiku 5 mani appointment podu, fee 500". Show intent + extracted fields + confirmation card -> appointment created | R2, R5 |
| 3:45-5:00 | Reminders | "Advance clock 24 h": outbox fires the T-24h reminder; the simulated phone shows the Tamil message; one live SMS to Lebi's phone via the gateway; one wa.me link opens WhatsApp prefilled | R2, R3 |
| 5:00-6:15 | No-show recovery + copilot | Mark an appointment no-show -> recovery task; click "Draft": Tamil / English / Tanglish variants from gpt-oss-120b; edit, consent check passes, send; simulated patient rebooks | R3, R5 |
| 6:15-7:15 | Recovered revenue + analytics | Dashboard: ₹ recovered this week, click through to the appointments behind it; no-show rate, response-time p50/p90 | R1, R3 |
| 7:15-8:00 | Trust | Lead score "why" panel; Tamil/English toggle on the same screen; consent/opt-out; audit log row for the send | R1, R5 |
| 8:00-9:00 | Engineering proof | OpenAPI `/docs`; test run summary; turn `AI_PROVIDER=off` and show chat still works with fallback replies | R2, R6 |
| 9:00-10:00 | Close | Limits + next steps (real clinic pilot); invite questions | R4 |

Fallbacks: Groq 429 -> say "this is the fallback path" and continue; no network -> switch to the backup video at the same timestamp; SMS phone fails -> show the outbox row and simulated phone only.

## 4. Deliverables

| Deliverable | Contents | Owner/notes |
|---|---|---|
| Project report (PDF + DOCX) | Title, certificate page, abstract, 1 Introduction (problem, users: clinics in TN), 2 Requirements (functional, non-functional, constraints: DPDP, TRAI, WhatsApp pricing), 3 Stack and equivalence, 4 Architecture (diagram, sequence diagrams), 5 Database design (ER with new tables, short), 6 API design (endpoint table), 7 Front-end design (design system, Tamil/English, screenshots), 8 AI layer (Groq models, structured outputs, fallback, privacy), 9 Background jobs and channels, 10 Testing (results), 11 Results (demo metrics on seed data, labelled as such), 12 Limitations and future work, references with access dates, appendix (faculty stack approval, run guide) | Write from scratch; do not paste DBMS chapters (section 6) |
| PPT (12-14 slides) | Problem; who it's for; stack equivalence; architecture; data model; key flows (lead -> booking -> reminder -> recovery); AI layer; Tamil/English UI; innovation (copilot, explainable score, SLA, recovered ₹); testing; results; limits/next steps; thanks + Q&A | Same diagrams as the report |
| Code | Git repo (or zip) with README: prerequisites, `cp .env.example .env`, `docker compose up -d`, seed command, demo login, test commands; `.env` excluded; `docs/` in sync | Tag the submitted commit (e.g. `ia3-submission`) |
| Demo assets | Backup video (8-10 min), seed script, printed architecture page | Record after the final build |
| Certificate | MongoDB certificate: separate 10-mark item, already handled by Lebi | Mention only |

## 5. Rubric risk register

| Risk | Rubric hit | Mitigation |
|---|---|---|
| Examiner insists on MongoDB/Node | All | Written faculty approval in the appendix + equivalence slide |
| Live AI call slow or rate-limited | R3, R5 | `reasoning_effort: low`, merged call, Developer tier, deterministic fallback, backup video |
| Tamil output wrong in front of examiner | R5 | Human-review step is part of the design; show eval numbers including failures |
| "This looks like your DBMS project" | R5, R6 | Section 6 changes: new domain, new modules, new report |
| Claims sound inflated | R4, R6 | Plain wording; label seed data, attributed revenue, synthetic training data |

## 6. Differentiation from the DBMS submission

Existing artefact: `docs/dbms_academic_report.{md,docx,pdf,html}`, titled "Database Management System for Renewable Energy Client Relationship Management (LivoCRM)". It frames LivoCRM as a B2B solar/wind sales CRM and spends most of its length on ER design, schema tables, 1NF-3NF normalisation, SQL aggregation and the synthetic ML data generator.

| Dimension | DBMS report (earlier) | IA3 submission (this) |
|---|---|---|
| Domain | B2B renewable energy sales (solar/wind installers) | Small Tamil Nadu clinics: patient follow-up desk (leads, appointments, reminders, no-show recovery) |
| Core objects | users, contacts, deals, activities, pipeline_stages | + appointments, leads/inbound events, messages/outbox, consents, audit_log, roles |
| Focus | Schema, normalisation, SQL analytics | Full-stack integration: UI/UX, REST + WebSocket, background worker, external AI and messaging channels, deployment |
| AI | Bedrock chat that creates records; unexplained lead score | Groq strict-JSON extraction, Tamil/Tanglish copilot, explainable score, Whisper voice notes, privacy controls |
| Language | English only | Tamil + English UI and messages |
| Metrics | Win rate, weighted forecast | Response time p50/p90, no-show rate, reminder delivery, ₹ recovered |
| Screenshots | Old dashboard/pipeline/chat | All new screens; none reused |
| Title (proposed) | - | "LivoCRM: A Bilingual (Tamil/English) Follow-up Desk for Small Clinics, with AI-Assisted Lead Capture, Reminders and No-show Recovery" |

Rules: no copied paragraphs, figures or code listings from the DBMS report; DB design gets one short chapter that cites the DBMS work as prior work ("schema hardening was done in an earlier course; this project extends it with..."); new screenshots only. The DBMS report's tone ("exquisitely crafted", "zenith of contemporary DBMS deployment") should not carry over; examiners reward plain, checkable claims.

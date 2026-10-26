# Full Stack IA3 report outline

Skeleton only. Write the prose in your own words, take screenshots from the running app, and fill every `TO FILL` with a real measurement. Evidence sources: `docs/plan/09-ia3-rubric-mapping.md` (rubric map, viva questions, demo script).

## 0. Reuse declaration (put on page 1)
LivoCRM was first built for the DBMS course (archived in `docs/archive/`). For IA3 it is a declared base. Table to complete:

| Area | Base (DBMS) | New for IA3 |
|---|---|---|
| Domain | Energy-sector B2B CRM | Clinic follow-up and no-show recovery |
| AI layer | AWS Bedrock | Groq provider with multi-key pool, EN/TA drafts |
| Data model | contacts, deals, activities, chat | + appointments, follow_up_tasks, outbound_messages (migration 0010) |
| UI | generic indigo dashboard | "Ledger" design, mobile-first, EN/TA toggle |
| Quality | no tests | 232 backend and 31 frontend tests, security fixes (`docs/security.md`) |

## 1. Front-end design (5)
HTML5 semantics, CSS3 (custom properties, grid/flex, dark mode), responsive breakpoints, React 19 component structure, accessibility. Screenshots: Today, Appointments, Reports at 360 px and desktop. TO FILL.

## 2. Back-end integration (5)
FastAPI layers, PostgreSQL schema and migrations, Redis (rate limits, tickets, locks), JWT and WebSocket tickets, Groq key pool, recovery engine. Diagrams from `docs/architecture.md`.

## 3. Functionality (5)
End-to-end scenario: missed call or booking, reminders, no-show, drafted recovery message, approval, recovered INR. Error and fallback behaviour (LLM down). TO FILL with demo results.

## 4. Presentation (5)
Demo script (9 min) and the 25 viva questions in `docs/plan/09-ia3-rubric-mapping.md`.

## 5. Innovation (5)
Bilingual draft copilot with human approval, attributed recovered-revenue metric, multi-key LLM load balancer with failover, simulation/seed mode.

## 6. Documentation (5)
Point to `docs/architecture.md`, `API.md`, `docker.md`, `ai.md`, `security.md`, `testing.md`.

## Appendix
Test report (counts and coverage: TO FILL after a fresh run), security summary, limitations (no workspaces/roles, simulated channel only, Tamil copy not natively reviewed).

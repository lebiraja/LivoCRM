# Plan docs: LivoCRM for IA3

Index of the planning set. Date: 2026-10-26. Stack is fixed (FastAPI, React/Vite, Postgres, Redis, Docker, Nginx); the AI layer moves to Groq.

| # | File | Owner | Purpose |
|---|---|---|---|
| 00 | `00-master-plan.md` | lead | **Approved master plan**: gated phases 0-7, Groq key pool, AWS Cloud IA3 |
| 01 | `01-code-audit.md` | audit-agent | Architecture as built, findings, doc-vs-code gaps, dead code |
| 02 | `02-security-review.md` | audit-agent | OWASP-style findings by severity with fixes |
| 03 | `03-implementation-plan.md` | audit-agent | Phased plan, estimates, acceptance criteria |
| 04 | `04-groq-migration.md` | audit-agent | Provider interface and Groq rollout |
| 05 | `05-testing-plan.md` | audit-agent | pytest, vitest, Playwright plan |
| 06 | `06-ui-audit-and-research.md` | ui-agent | Current UI audit and cited research |
| 07 | `07-ui-redesign-plan.md` | ui-agent | Design system, wireframes, phases |
| 08 | `08-feature-research.md` | research-agent | Groq models, ranked feature backlog, competitors |
| 09 | `09-ia3-rubric-mapping.md` | research-agent | Rubric evidence, viva questions, demo script |

Root tracking files: `HANDOVER.md`, `STATUS.md`, `FIXES.md`, `CHECKLIST.md`, `VERSIONS.md`.

Reading order for a new session: `HANDOVER.md` → this index → `00` → `03` → `02` → `04` → `07` → `09`.

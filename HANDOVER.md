# HANDOVER

> Version: v0.2.0-secure · Last changed: 2026-10-26

## Current (v0.2.0-secure)

### What this is
LivoCRM reused for Full Stack Development IA3 (30 marks: front-end, back-end, functionality, presentation, innovation, documentation) and as a demo for the Tamil follow-up desk startup idea (clinics first). Stack: FastAPI, React/Vite + Tailwind + shadcn/ui, PostgreSQL, Redis, Nginx, Docker Compose. **Do not change the stack.** AI layer is moving to the Groq API.

### Where we are
Phase 0 (gate 0) is done and merged: security fixes, tests, cleanup. Master plan: `docs/plan/00-master-plan.md`. Next is Phase 1 (Groq provider + multi-key pool); the three Groq keys are in the gitignored `.env` as `GROQ_API_KEYS`. Estimated work is 128-178 h; scope must be cut before starting. Read, in this order:
1. `docs/plan/README.md` (index of all plan docs)
2. `docs/plan/03-implementation-plan.md` (phased work)
3. `docs/plan/02-security-review.md` (Phase 0 fixes)
4. `docs/plan/04-groq-migration.md`
5. `docs/plan/07-ui-redesign-plan.md`
6. `docs/plan/09-ia3-rubric-mapping.md`

### Next session, do this first
1. Review the reports with Lebi; agree the cut scope. Suggested keep: Phase 0, Groq migration, follow-up queue and reminder outbox, Tamil/English toggle, Ledger redesign, report and demo kit.
2. Start Phase 0 from the implementation plan; log each fix in `FIXES.md`.
3. Then the Groq migration, then UI, then features.

### Open items
- IA3 deadline not known; case study wording not seen (faculty confirmed reuse, per Lebi)
- `origin` is still `lebiraja/LivoCRM` (the DBMS submission); decide on a new remote
- Groq API key needed from Lebi (never commit it); enable zero data retention
- Rotate the committed Postgres/pgAdmin passwords (SEC-01) before anything is deployed
- Groq model names to verify in the Groq console before coding (`openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `whisper-large-v3`)
- Previous DBMS report in `docs/dbms_academic_report.*`: IA3 must be visibly different

### Gotchas
- Run everything in Docker; services talk by network names
- Tests: `docker compose run --rm <service> pytest`
- Upstream docs in `docs/` were written for the earlier version; trust the code where they disagree (discrepancies are listed in `docs/plan/01-code-audit.md`)
- Use they/them or Lebi for Lebi; never guess pronouns

## Previous versions
_None._

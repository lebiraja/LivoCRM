# HANDOVER

> Version: v0.7.0-prod-cloudflare · Last changed: 2026-10-27

## Current (v0.7.0-prod-cloudflare)

### What this is
LivoCRM reused for Full Stack Development IA3 and the Cloud Computing IA3 demo. Stack: FastAPI, React/Vite + Tailwind + shadcn/ui, PostgreSQL, Redis, Nginx, Docker Compose. The frontend has been restored to the original cloned UI; Tamil and the Ledger redesign were removed. Groq powers the AI backend.

### Where we are
Phases 0-4 and the Cloud artifacts are merged to `main`; synthetic pipeline demo data is included. The original UI exposes Dashboard, Contacts, Pipeline, Chat, Analytics and Settings. Appointments/recovery remain API-only. Production deployment files and runbook are in `cloud/deploy/cloudflare-server.md`; they use Cloudflare Tunnel, secure HttpOnly browser cookies, and a CLI-created first account. Compose config was checked, but test/image builds were not run because the package registry could not resolve and Lebi asked not to build locally. Remaining: fill server `.env`, create Cloudflare tunnel/route, deploy, set off-server backups, and write IA3 reports/PPT. Read:
1. `docs/plan/README.md` (index of all plan docs)
2. `docs/plan/03-implementation-plan.md` (phased work)
3. `docs/plan/02-security-review.md` (Phase 0 fixes)
4. `docs/plan/04-groq-migration.md`
5. `docs/plan/07-ui-redesign-plan.md`
6. `docs/plan/09-ia3-rubric-mapping.md`

### Next session, do this first
1. Follow `cloud/deploy/cloudflare-server.md` on the server after creating the Cloudflare route for `livocrm.lebiraja.in`.
2. Build and start the stack on the server; create the initial login with `python -m app.cli create-user`.
3. Verify HTTPS login and health, then configure an off-server backup destination and test a restore.

### Open items
- IA3 deadline not known; case study wording not seen (faculty confirmed reuse, per Lebi)
- The repo remote is `lebiraja/LivoCRM`; push was explicitly requested for this deployment work.
- Keep the previously supplied Groq keys and the Cloudflare Tunnel token in server-only secret storage, never Git.
- Rotate any real Postgres, Redis, or JWT secrets reused from an earlier `.env` before deployment.
- Single-server deployment; MFA, password reset, email verification and session-token revocation are not implemented.
- Off-server backup destination and restore rehearsal remain operator tasks.

### Gotchas
- Run everything in Docker; services talk by network names
- Tests: `docker compose run --rm <service> pytest`
- Upstream docs in `docs/` were written for the earlier version; trust the code where they disagree (discrepancies are listed in `docs/plan/01-code-audit.md`)
- Use they/them or Lebi for Lebi; never guess pronouns

## Previous versions
_None._

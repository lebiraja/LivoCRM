# VERSIONS

Version history for the IA3 build of LivoCRM. Newest on top. Bump the version and add a row for every tagged milestone.

| Version | Date | Summary |
|---|---|---|
| v0.7.0-prod-cloudflare | 2026-10-27 | Production Cloudflare Tunnel compose, HttpOnly login cookies, private registration, secure account CLI, deployment runbook and local backup script. Config validated; app images/tests not run. |
| v0.6.0-docs | 2026-10-26 | Phase 4: current docs, archived old docs, report outlines. |
| v0.5.0-ui | 2026-10-26 | Phases 2, 3, 6 merged: clinic engine, Ledger UI, AWS artifacts. 232 backend + 31 frontend + 38 cloud tests. |
| v0.4.0-clinic | 2026-10-26 | Gate 2: appointments, recovery engine, drafts, seed demo. |
| v0.3.0-groq | 2026-10-26 | Gate 1 (lean): Groq provider, multi-key pool, AI health endpoint, 161 backend tests. |
| v0.2.0-secure | 2026-10-26 | Gate 0: security and data-integrity fixes, test harness (138 backend + 15 frontend tests), dead code removed. |
| v0.1.0-ia3-plan | 2026-10-26 | Cloned LivoCRM into `full-stack/`. Audit, security review, UI research, feature research and implementation plans written under `docs/plan/`. Tracking files created. No source code changed. |
| v0.0.0-baseline | 2026-04-08 | Upstream LivoCRM at `c82bbcd` (FastAPI + React + Postgres + Redis, AWS Bedrock AI layer). Starting point for IA3. |

## Versioning rules
- `v0.x` while the plan and fixes land; `v1.0.0` is the IA3 submission build.
- Each version: one row here, one `STATUS.md` entry, and a git tag when code changes.
- Do not push to the upstream `origin` (`lebiraja/LivoCRM`) without deciding to; the DBMS submission was made from it.

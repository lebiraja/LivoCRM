# STATUS

Session log. Newest entry on top.

## 2026-10-26 · v0.2.0-secure · Phase 0 complete (gate 0)
- **Done:** Test harness (138 backend tests, 81% coverage; 15 frontend tests), SEC-01 to SEC-28 stop-ship fixes, WebSocket tickets, PyJWT, rate limiting, PII-free logging, container and nginx hardening, 41 dead frontend files removed, fonts self-hosted, fake UI data removed. 14 issues opened (#6-#19). Verified by lead: pytest 138 passed, ruff clean, compose policy ok, frontend build + vitest + eslint clean.
- **Open:** `pip-audit` flags Starlette 0.38.6 (needs FastAPI upgrade, planned in Phase 1/4); mypy has 22 pre-existing errors (not a gate yet); SEC-11 token storage, SEC-29 DPDP data export/delete, WS close at token expiry are later phases.
- **Incident:** a backend-agent script rebuilt the local `.env` and dropped the Groq keys; re-added by hand. Keys live only in the gitignored `.env`.
- **Next:** Phase 1 (Groq provider + key pool). Requires asking Lebi before spawning agents (new CLAUDE.md rule).

## 2026-10-26 · v0.1.0-ia3-plan · Clone, audit and planning
- **Done:** Cloned `lebiraja/LivoCRM` (HEAD `c82bbcd`, 15 commits, sole contributor) into `full-stack/LivoCRM`. Launched three agents: code and security audit, UI research and redesign plan, feature and rubric research. Created `HANDOVER.md`, `STATUS.md`, `FIXES.md`, `CHECKLIST.md`, `VERSIONS.md` and `docs/plan/`.
- **Decisions:** Stack stays as is (FastAPI, React/Vite, Postgres, Redis, Docker, Nginx). AI layer moves to the Groq API. Faculty confirmed (per Lebi) that this project is acceptable for IA3. The repo is reused from the DBMS course, so IA3 must show visibly new work.
- **Blockers / open:** Exact IA3 deadline unknown. Case study text still unseen. `origin` still points to the upstream repo; decide whether to create a new repo before pushing.
- **Agent results (all 9 plan docs written, ~1900 lines, no source touched):**
  - Audit: 29 security findings (2 Critical, 6 High, 13 Medium, 8 Low) and 31 code findings. No tests or CI exist. Critical: Postgres 5435 and pgAdmin 5050 published with committed/default passwords (SEC-01); open registration plus blocking boto3 call in an async handler (SEC-02).
  - UI: direction "Ledger" (editorial-minimal, paper/ink, deep-green accent, ruled rows, Today follow-up queue, mobile bottom nav, Tamil/English toggle). Bundle and Lighthouse numbers unmeasured `[?]`.
  - Research: Groq models `openai/gpt-oss-20b` (classify/extract), `openai/gpt-oss-120b` (Tamil drafts), `whisper-large-v3` (STT). Llama 3.x and Llama 4 Scout are shut down on Groq free/dev tiers. 8K TPM limit means ~2-3 chat turns a minute. Enable ZDR.
  - Plan: Phases 0-5, 128-178 h total. Scope cut needed.
- **Next:** Lebi approves scope and order; start Phase 0 (SEC-01..06), logging each fix in `FIXES.md`.

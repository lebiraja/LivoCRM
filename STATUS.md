# STATUS

Session log. Newest entry on top.

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

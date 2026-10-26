# STATUS

Session log. Newest entry on top.

## 2026-10-26 · v0.5.0-ui · Phases 2, 3 and 6 merged (lean scope)
- **Phase 2 (v0.4.0-clinic):** migration 0010 (appointments, follow_up_tasks, outbound_messages), idempotent recovery engine, Groq draft copilot with EN/TA template fallback, summary with attributed recovered INR, seed CLI. 232 backend tests, 85% coverage. Scope cut: per-user ownership (no workspaces/roles), simulated channel only.
- **Phase 3:** "Ledger" UI (paper/ink, deep-green accent, bottom nav on mobile, EN/TA toggle), Today, Appointments, Reports, Settings with AI key health; 31 frontend tests. Lead check on integration found two contract mismatches the agent had guessed wrong (appointments lacked `contact_name`; `/ai/health` shape); fixed with tests. Entry bundle 210 kB gzip (budget 180).
- **Phase 6 (PR #22):** SAM template, ETL and score Lambdas, SageMaker training code, Caddy TLS prod override, EC2 runbook; 38 tests; workflow set to manual until AWS exists. Nothing deployed.
- **Open:** deployment needs Lebi's AWS console steps (`cloud/deploy/README.md`); Tamil copy unreviewed by a native speaker; no 360 px browser check; Leads/lead-detail screens not built; docs (`architecture.md`, `docker.md`, `API.md`, `ai.md`, cloud report outline) and IA3 reports still to write (Phase 4); strict json_schema output and Bedrock removal deferred.

## 2026-10-26 · v0.3.0-groq · Phase 1 (lean): Groq provider with multi-key pool
- **Done:** `app/services/llm/key_pool.py` (load balancing by remaining tokens, 429 cooldown and instant failover, 401 disable, secrets only as key ids) and `groq_client.py` (httpx, strict timeouts, 4 attempts max, no content in logs); `chat_completion` and insights dispatch on `LLM_PROVIDER` (default `groq`, Bedrock kept as legacy); `GET /api/ai/health` shows per-key state without secrets; `.env.example` documents `GROQ_API_KEYS` (1 to N keys). 23 new tests; full suite 161 passed, 82% coverage, ruff clean.
- **Verified live:** both `openai/gpt-oss-20b` and `openai/gpt-oss-120b` answer on the account (8,000 TPM, 1,000 RPD); 6 live calls through the 3-key pool spread 2 per key.
- **Deviations from plan:** key state is per process (not Redis); sync client inside `to_thread` (no full async rewrite); strict json_schema, budget guard, confirm endpoint and Bedrock removal deferred (interim negation-safe confirm from Phase 0 stays).
- **Caveat:** Groq limits are per organisation; keys from one org share a bucket. Rotate the keys after the demo (they were pasted in chat).
- **Found while testing:** own bug in the first draft (retry helper returned text for failures); caught by the failover test before merge.
- **Next:** Phase 2/3/6 are running in parallel as Haiku agents in worktrees (p2-backend, p3-frontend, p6-cloud).

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

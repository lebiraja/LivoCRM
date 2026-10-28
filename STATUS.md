# STATUS

Session log. Newest entry on top.

## 2026-10-28 · v0.7.2-cicd · CI/CD to the server, Groq keys live
- **Done:** `.github/workflows/ci.yml` (gitleaks, compose policy + prod config check, backend tests in the compose test profile, frontend lint + build, production image builds) and `deploy-server.yml` (after green CI on main: SSH to the server, `scripts/deploy-server.sh <sha>` builds, `up -d --wait`, rolls back to the previous commit on failure; then HTTPS smoke test). The older `deploy.yml` (AWS ECR/SSM) stays manual-only. Groq keys (3) copied to the server `.env`; backend recreated and sees them.
- **GitHub setup:** secrets `DEPLOY_SSH_KEY` (dedicated ed25519 key, public half in server `authorized_keys`), `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_KNOWN_HOSTS`; variable `APP_URL`; environment `production`.
- **Fix on the way:** frontend lint was failing (unused `err` in ContactsPage, shadcn `only-export-components`); fixed so CI is green.
- **Verification:** CI run and deploy run both green; `/api/health` ok through the tunnel.
- **Open:** server public IP is not an Elastic IP (it changed between sessions), update `DEPLOY_HOST` if it changes; branch protection requiring CI on main not set.

## 2026-10-28 · v0.7.1-deployed · Live on EC2 behind Cloudflare Tunnel
- **Done:** deployed to the Ubuntu 24.04 EC2 host at `~/LivoCRM`; all six services healthy, no host ports published. `https://livocrm.lebiraja.in` serves the app and `/api/health`; first account created via `app.cli create-user`, API login verified through the public URL.
- **Tunnel:** `TUNNEL_TOKEN` now comes from `.env` (only passed to `cloudflared`), tunnel has a healthcheck and `--url http://nginx:80`. Tunnel `livocrm` was created from the server with `scripts/cf-tunnel-setup.sh <host>` (cloudflared login link, no dashboard token copy); the account cert is deleted after use. The Docker-secret file approach was dropped.
- **Gotchas:** the login link authorizes the `lebiraja.in` zone, so pass the full hostname `livocrm.lebiraja.in` (a `.tech` host became `livocrm.lebiraja.tech.lebiraja.in`; delete that stray CNAME). Password minimum is 10 characters.
- **Open:** off-server backups and restore rehearsal; rotate the SSH key and Groq keys that were pasted in chat; `GROQ_API_KEYS` still empty on the server (rule-based AI fallback).

## 2026-10-27 · v0.7.0-prod-cloudflare · Production deployment prep
- **Done:** Cloudflare Tunnel Compose ingress, private tunnel-to-Nginx network, client IP forwarding for rate limits, production environment template, HTTPS-only browser cookies, public registration disabled, password-prompting account CLI, local PostgreSQL backup script, updated deployment/security docs. Nginx host port is removed in the production override.
- **Verification:** Compose config, backup script syntax, and whitespace checks pass. Backend test image build was stopped after external package DNS resolution failed; no app image was built per Lebi's instruction.
- **Deploy prerequisites:** create a Cloudflare named tunnel and published route (`livocrm.lebiraja.in` → `http://nginx:80`), put its token in `.secrets/cloudflare_tunnel_token`, fill `.env` from `.env.production.example`, then follow `cloud/deploy/cloudflare-server.md`. Local server setup remains for Lebi to do.
- **Known limits:** single server; no MFA, password reset/email verification, JWT deny-list, or automated off-host backup. Groq keys and the Cloudflare token must stay out of Git.

## 2026-10-26 · v0.6.0-docs · Phase 4 docs
- **Done:** `docs/architecture.md`, `docker.md`, `API.md`, `ai.md`, `security.md`, `testing.md`, refreshed `README.md`, both IA3 report outlines (`docs/ia3-fullstack-report-outline.md`, `docs/cloud/report-outline.md`, skeletons with `TO FILL` markers, no invented results). Stale pre-IA3 docs moved to `docs/archive/`.
- **Caveat:** docs were written by a Haiku agent from code; test counts and coverage are copied from STATUS, not re-run in that pass. Re-verify before submission.
- **Open:** final frontend build on main not re-run (network dropped); AWS deployment pending (issue #19); case study, deadlines, cloud certificate course still unknown; reports to write.

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

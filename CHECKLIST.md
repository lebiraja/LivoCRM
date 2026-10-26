# CHECKLIST

Master checklist for the IA3 build. Tick items as they are verified, not when started. Detailed tasks live in `docs/plan/03-implementation-plan.md` and `docs/plan/07-ui-redesign-plan.md`.

## 0. Setup and planning
- [x] Clone LivoCRM into `full-stack/LivoCRM`
- [x] Tracking files (`HANDOVER`, `STATUS`, `FIXES`, `CHECKLIST`, `VERSIONS`)
- [x] Audit, security, UI and feature reports written (`docs/plan/01`-`09`)
- [ ] Reports reviewed with Lebi and scope cut agreed
- [ ] Decide on a new git remote (do not push to upstream by accident)
- [ ] Confirm IA3 deadline and the case study wording with Dr. Jenefa

## 1. Phase 0: stop-ship fixes (from audit)
- [ ] Critical security findings fixed and logged in `FIXES.md`
- [ ] Data-integrity and session-state findings fixed
- [ ] `frontend/tmp-scaffold` removed
- [ ] No secrets in repo or history; `.env.example` complete

## 2. Groq migration
- [ ] Provider interface in place, Bedrock path removed or optional
- [ ] Groq models chosen per task (see `docs/plan/08-feature-research.md`)
- [ ] Structured outputs, timeouts, retries, fallback
- [ ] `GROQ_API_KEY` in `.env.example` and docs

## 3. Features (IA3 and startup demo)
- [ ] Top features from the ranked backlog built
- [ ] Seeded demo data and simulation mode
- [ ] Tamil/English toggle

## 4. UI
- [ ] Design system tokens and fonts (Tamil-safe)
- [ ] Every page redesigned, mobile first
- [ ] Lighthouse and a11y targets met

## 5. Quality
- [ ] pytest (auth and data mutations fully covered), vitest, Playwright smoke
- [ ] `docker compose up` clean from scratch, healthchecks green
- [ ] Docs in `docs/` match the code (use `docs-keeper`)

## 6. IA3 deliverables
- [ ] Project report
- [ ] PPT
- [ ] Code (clean repo, README)
- [ ] MongoDB certificate (handled separately, already downloaded in `../cert/`)
- [ ] Demo script rehearsed (see `docs/plan/09-ia3-rubric-mapping.md`)
- [ ] Uploaded to GCR

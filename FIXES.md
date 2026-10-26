# FIXES

Real bug fixes only. Newest on top. Each entry: symptom, root cause, fix with `file:line`, verification.

_Findings come from `docs/plan/01-code-audit.md` and `docs/plan/02-security-review.md`; each one that gets fixed is logged below the template._

## Entry template
```
## YYYY-MM-DD · <short title>
- **Symptom:** what the user or test saw
- **Root cause:** why it happened
- **Fix:** what changed, `path/file.py:line`
- **Verification:** test name or command and result
- **Finding ref:** ID from docs/plan/
```

## 2026-10-26 · Postgres and pgAdmin published with committed default passwords
- **Symptom:** `docker compose up` published Postgres on `0.0.0.0:5435` and pgAdmin on `0.0.0.0:5050`; pgAdmin's password was hard-coded in `docker-compose.yml`, and the DB password was committed in `.env.example`, `backend/.env.example` and `docs/pgadmin_setup.md`.
- **Root cause:** dev conveniences (host ports, inline credentials, `:latest` image) shipped in the default compose profile; no secret scanning.
- **Fix:** removed `db.ports` (`docker-compose.yml:13`); pgAdmin moved to `profiles: ["dev"]`, bound to `127.0.0.1:5050`, credentials from `.env`, image pinned to `9.18` (`docker-compose.yml:76-84`); Postgres/Redis images pinned to `16.15-alpine`/`7.4.11-alpine`; `change-me` placeholders in `.env.example:6,8,11,18`; `backend/.env.example` deleted (duplicate, CA-29); `docs/pgadmin_setup.md:10,20,42` uses env names; gitleaks pre-commit hook `v8.30.1` (`.pre-commit-config.yaml`); policy script `scripts/check_compose_policy.py`. Lebi action: rotate any real `.env` that reused the old values.
- **Verification:** `python3 scripts/check_compose_policy.py` failed with 9 violations before, prints `compose policy: ok` after; `gitleaks git` over 16 commits: no leaks found.
- **Finding ref:** SEC-01

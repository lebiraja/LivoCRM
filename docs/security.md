# Security

Findings come from `docs/plan/02-security-review.md` (SEC-01 to SEC-29, static review). Fixes are logged in
`FIXES.md` with file:line references. This page maps each finding to its current state and to the code that
enforces it. Status: **Fixed** (in code, with tests), **Partial**, **Open**.

## Phase 0 status

| ID | Finding | Status | Where it is enforced | Evidence |
|---|---|---|---|---|
| SEC-01 | Postgres and pgAdmin published with committed default passwords | Fixed | `docker-compose.yml`: no `db` ports; pgAdmin on `profiles: [dev]`, bound to `127.0.0.1:5050`, image pinned; `change-me` placeholders in `.env.example`; gitleaks pre-commit hook; `scripts/check_compose_policy.py` | FIXES: "Postgres and pgAdmin published…". Rotating any real secret that reused the old values is an operator step |
| SEC-02 | Synchronous LLM call froze the event loop; boto3 default timeouts | Fixed (interim) | `bedrock_service.py`: `llm_slots` semaphore (8), boto3 `Config` 3 s / 15 s; `routers/chat.py`: `asyncio.to_thread`; Groq `httpx` timeouts | FIXES: "Synchronous Bedrock call…". Async provider client deferred |
| SEC-03 | No rate limiting, lockout or quota | Fixed | `services/rate_limit.py` (Redis fixed window, `Retry-After`); limits in `docs/API.md`; nginx `limit_req` zones `auth` and `api`. Fails open when Redis is down, logged as a warning | FIXES: "No rate limiting…"; `test_rate_limit_*` |
| SEC-04 | "no, don't save" saved the record | Fixed (interim) | `orchestrator.parse_confirmation`: negation words checked first | FIXES; `test_confirmation.py` (25 utterances), `test_no_dont_save_saves_nothing` |
| SEC-05 | LLM output trusted before DB writes | Fixed | `schemas/ai_actions.py` (`extra="forbid"`, closed enums, `Decimal`); `data_extractor.py` keeps schema keys only; targets matched by exact name, else a clarification | FIXES: "LLM output written to the database unvalidated…" |
| SEC-06 | Failed save violated CHECKs and poisoned the transaction | Fixed | `chat.py`: `db.begin_nested()` savepoint per save; migration `0009` adds `failed` to `ck_chat_actions_status` | FIXES: "A bad AI value turned the save into a 500…"; `test_migrations.py` |
| SEC-07 | DB connection held across LLM round-trips | Fixed for chat and drafts | `chat.py` and `follow_ups.py` commit before the LLM call. `ai.py` insights still holds its session across its call (see `docs/architecture.md` section 5) | FIXES; `test_pool_not_held_during_llm` |
| SEC-08 | Parallel confirmations created duplicates | Fixed | `session_manager.session_lock`: Redis `SET NX PX 30000`, owner-checked release; busy turn returns 409 | FIXES; `test_concurrent_confirm_single_entity` |
| SEC-09 | Foreign keys accepted across tenants | Fixed | `services/ownership.require_owned()` on deal, activity and appointment writes | FIXES; `test_cross_tenant_fk_reference_rejected` |
| SEC-10 | JWT in WebSocket URL, written to logs | Fixed | Single-use 30 s tickets (`ws_tickets.py`, `GETDEL`); nginx `log_format noargs` uses `$uri` | FIXES: "JWT carried in WebSocket URLs…"; `test_ticket_admits_once`, `test_raw_jwt_rejected` |
| SEC-11 | Token in `localStorage`; no logout or revocation | **Open** (partial) | `auth_service.py` adds `iat` and random `jti`. Token still lives in `localStorage` (`frontend/src/api/client.ts`). No refresh, no deny-list; a token is valid until `exp` | FIXES (iat/jti part only) |
| SEC-12 | Weak registration and login | Fixed | Password 10-72 UTF-8 bytes (`schemas/user.py`); lower-cased email with unique `lower(email)` index (`0008`); `DUMMY_HASH` on unknown user; generic 409 | FIXES: "Weak registration and login hygiene…" |
| SEC-13 | PII in logs and raw model output | Fixed | `logging_config.py` masks emails, phones and URL query strings; extractor and classifier log type and length only | FIXES: "PII and raw model output in logs…"; `test_no_pii_in_logs` |
| SEC-14 | Input validation gaps caused 500s | Fixed | Typed, bounded schemas; `IntegrityError` to 409, `DataError` to 422 (`main.py`); nginx `client_max_body_size 1m` | FIXES: "Invalid input reached the database…"; `test_invalid_payloads_return_422` |
| SEC-15 | Events published before commit | Fixed | `chat.py`: commit, then Redis context, then publish | FIXES; `test_event_published_after_commit` |
| SEC-16 | Vulnerable or unpinned dependencies | **Partial** | `python-jose` replaced by `PyJWT==2.15.1`; all backend pins exact. Open: `pip-audit` reports Starlette 0.38.6 advisories through `fastapi==0.115.0`; needs a FastAPI upgrade | FIXES: "python-jose…"; `STATUS.md` v0.2.0 |
| SEC-17 | Container hardening | Fixed | Runtime user uid 10001; `backend/.dockerignore`; `db` has no `env_file`; healthchecks on all default services; pinned image tags | FIXES: "Containers ran as root…" |
| SEC-18 | Edge headers, CSP, server version | Fixed (HSTS open) | `nginx/nginx.conf`: CSP, `X-Frame-Options DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, `server_tokens off`. HSTS is not set anywhere in the repo; the prod `Caddyfile` terminates TLS with no HSTS header | FIXES: "Edge hardening…" |
| SEC-19 | WebSocket authorisation and lifecycle | Fixed | Chat tickets bound to the caller's own session (`websocket.py`); 5-socket cap with close 4029; `finally` cleanup; catch-all in the loop. Socket lifetime is not bounded by token expiry | FIXES: "WebSocket lifecycle…"; `test_connection_cap_per_user` |
| SEC-20 | AI session store unbounded and unbound to owner | Fixed | Redis only: `livocrm:ctx:<user>:<session>`, 1 h TTL | FIXES; `test_context_bound_to_user` |
| SEC-21 | No prompt-injection hardening on non-write paths | **Open** | Not in `FIXES.md`. Untrusted text is still concatenated into prompts without delimiters (`prompts.py`, `data_extractor.py`). Writes are gated by schema validation and confirmation, which limits the impact | `docs/ai.md` |
| SEC-22 | Non-UUID `sub` returned 500 | Fixed | `dependencies.get_current_user` returns 401 | FIXES; `test_bad_sub_is_401` |
| SEC-23 | CORS hard-coded; all methods and headers allowed | Fixed | `CORS_ORIGINS` from env; methods limited to GET, POST, PATCH, DELETE, OPTIONS; headers to Authorization and Content-Type | FIXES; `test_cors_origins_from_env` |
| SEC-24 | `joblib.load` on a pickle | Fixed (mitigated) | Runtime image: `ml/model.pkl` root-owned and read-only to the app user. Pickle still loaded | FIXES: "Containers ran as root…" |
| SEC-25 | LIKE wildcards in search | Fixed | `icontains(..., autoescape=True)` in `contacts.py`; search capped at 100 chars | FIXES; `test_contact_search_escapes_wildcards` |
| SEC-26 | OpenAPI open by default; model id returned | Fixed | `ENABLE_DOCS=false` by default; `generated_by` is `"ai"` or `"fallback"` | FIXES; `test_api_docs_disabled_by_default`, `test_generated_by_hides_model_id` |
| SEC-27 | Fonts from a third-party CDN | Fixed | `@fontsource-variable/*` packages imported in `frontend/src/main.tsx`. No FIXES entry | `STATUS.md` v0.2.0 |
| SEC-28 | Redis without auth or memory cap | Fixed | `--requirepass`, `--maxmemory`, `allkeys-lru`; authenticated healthcheck | FIXES: "Redis without a password or memory cap" |
| SEC-29 | No account deletion, data export or consent record | **Open** | No such endpoints (`docs/API.md`, "Routes not present"). Needed for DPDP handling of patient data | `docs/plan/02-security-review.md` |

## Checked and found clean (static review)

- SQL injection: all queries are SQLAlchemy expressions with bound parameters.
- Mass assignment: create and update schemas whitelist fields. `user_id`, `lead_score`, `source` and `plan`
  cannot be set by a client.
- IDOR on read, update and delete: every lookup filters on `user_id`, and a miss returns 404.
- XSS: React escapes output. No `dangerouslySetInnerHTML` in `frontend/src`. Model text renders as plain text.
- SSRF: no outbound URL is built from user input. Provider base URLs come from the environment.
- File upload: no upload endpoint exists.

## Data egress to the LLM provider

- Chat text is sent to Groq for classification, extraction and questions. It can contain names, phone numbers
  and emails that a user types, so this is personal data leaving the app.
- Follow-up drafts send the message purpose and the IST appointment time only. No name, phone or note.
- Groq zero-data-retention is listed as an open item in `HANDOVER.md`. Whether it is enabled on the account is
  `[?]`, not verified from code.
- Under DPDP the clinic is the data fiduciary and LivoCRM the processor. A notice and consent flow (SEC-29) does not
  exist yet.

## Authentication model

- Bearer JWT (HS256) signed with `SECRET_KEY` (at least 32 characters, enforced at start-up). Claims: `sub`,
  `iat`, `exp`, `jti`. Decoding requires `exp` and `iat`.
- Lifetime is `ACCESS_TOKEN_EXPIRE_MINUTES`: 480 in `.env.example`, 30 in code if unset. There is no
  revocation before expiry (SEC-11).
- Passwords: bcrypt via `bcrypt.gensalt()`.
- Roles: none. Every account is a single owner. A clinic with several staff would need RBAC first.

## Open items, in priority order

1. **SEC-29** account deletion, data export and a consent record for DPDP.
2. **SEC-11** token storage: move the token out of `localStorage`, or add refresh and a logout deny-list.
3. **SEC-16** Starlette advisories: upgrade FastAPI, then re-run `pip-audit`.
4. **SEC-21** delimit untrusted text in prompts and cap prompt sizes on read-only paths.
5. HSTS at the TLS terminator (`cloud/deploy/Caddyfile`).
6. Insights endpoint holds its DB session across the LLM call (`docs/architecture.md` section 5).
7. Rate limiter and session lock fail open when Redis is down. Chosen for availability; it weakens login
   throttling during a Redis outage. nginx `limit_req` remains as the second layer.

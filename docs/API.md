# LivoCRM API

Source: `backend/app/routers/*.py`, `backend/app/schemas/*.py`. All REST paths are under `/api`.
Browsers reach them through nginx on `http://localhost:3500`. The backend port is not published.

## Conventions

- **Auth.** `Authorization: Bearer <JWT>` (HS256; claims `sub` = user UUID, `iat`, `exp`, `jti`). Missing or
  invalid token: `401 {"detail": "Not authenticated"}` or `"Invalid or expired token"`. Every query is scoped
  to the caller's `user_id`; another user's id returns `404`.
- **Pagination.** Collection endpoints marked *paged* take `skip` (default 0) and `limit`. Response shape:
  `{"total": int, "items": [...]}`.
- **Timestamps.** ISO 8601 with timezone. Naive datetimes are rejected with `422` where a timezone is required.
- **Money.** `Decimal` fields serialize as JSON strings (`"400.00"`). Frontend coerces them with `z.coerce.number()`.
  `deals.value` is a JSON number.
- **Trailing slashes.** Use the exact paths below. Collections under `/contacts/`, `/deals/`, `/activities/`
  and `/pipeline-stages/` end in `/`. `/appointments`, `/follow-ups` and `/chat/sessions` do not.
- **Errors.** Handled errors: `{"detail": "<message>"}`. Schema validation: `422` with FastAPI's
  `{"detail": [{"loc", "msg", "type"}]}`. Database integrity violation: `409 {"detail": "Conflicts with existing data"}`.
  Database value rejection: `422 {"detail": "Invalid data"}`. Unhandled: `500 {"detail": "Internal server error"}`.
- **Rate limits.** Redis fixed window per key, returned as `429 {"detail": "Too many requests, try again later"}`
  with `Retry-After` in seconds. Edge (nginx) limits sit in front: `/api/auth/login|register` at 10 req/min
  per IP (burst 10), all other `/api/*` at 20 req/s per IP (burst 40). Edge 429s carry `Retry-After: 60`.
- **Docs.** `/api/docs` and `/api/openapi.json` exist only when `ENABLE_DOCS=true`.

## Health

| Method | Path | Auth | Response | Errors |
|---|---|---|---|---|
| GET | `/api/health` | none | `{"status": "ok"}` (no dependency checks) | - |

nginx also serves `GET /healthz` (plain `ok`), used by the container healthcheck.

## Auth (`/api/auth`)

| Method | Path | Auth | Rate limit | Body | Success | Errors |
|---|---|---|---|---|---|---|
| POST | `/api/auth/register` | none | 3 per hour per client IP | `UserCreate` | `201` `UserRead` | `409` "Could not register with these details"; `422` |
| POST | `/api/auth/login` | none | 5 per 60 s per IP+email | `LoginRequest` | `200` `Token` | `401` "Invalid credentials"; `429` |
| GET | `/api/auth/me` | Bearer | - | - | `200` `UserRead` | `401` |

- `UserCreate`: `email` (valid address, stored lower-case), `password` (10 to 72 UTF-8 bytes), `full_name`
  (max 255, default `""`). Registration seeds six default pipeline stages (Lead to Closed Lost).
- `LoginRequest`: `email`, `password`.
- `Token`: `{"access_token": str, "token_type": "bearer"}`. Lifetime is `ACCESS_TOKEN_EXPIRE_MINUTES`.
- `UserRead`: `{id, email, full_name, plan, created_at}`.

## Contacts (`/api/contacts/`)

| Method | Path | Auth | Body | Success | Errors |
|---|---|---|---|---|---|
| GET | `/api/contacts/` | Bearer | query: `skip`, `limit` (1-200, default 50), `search` (max 100; `%` and `_` are literal) | `200` paged `ContactRead`, newest first | `401` |
| GET | `/api/contacts/{contact_id}` | Bearer | - | `200` `ContactRead` | `404` "Contact not found" |
| POST | `/api/contacts/` | Bearer | `ContactCreate` | `201` `ContactRead` | `422` |
| PATCH | `/api/contacts/{contact_id}` | Bearer | `ContactUpdate` (all optional, `null` rejected) | `200` `ContactRead` | `404`, `422` |
| DELETE | `/api/contacts/{contact_id}` | Bearer | - | `204` | `404` |

- `ContactCreate`: `name` (1-255, required), `email` (valid address or `""`), `phone` (max 50), `company`
  (max 255), `tags` (max 20 items of 1-50 chars), `notes` (max 5000). Defaults are empty strings and `[]`.
- `ContactRead`: `{id, user_id, name, email, phone, company, tags, lead_score, notes, created_at, updated_at}`.

## Deals (`/api/deals/`)

| Method | Path | Auth | Body | Success | Errors |
|---|---|---|---|---|---|
| GET | `/api/deals/` | Bearer | query: `skip`, `limit`, `stage`, `status` (exact-match filters) | `200` paged `DealRead`, newest first | `401` |
| GET | `/api/deals/{deal_id}` | Bearer | - | `200` `DealRead` | `404` "Deal not found" |
| POST | `/api/deals/` | Bearer | `DealCreate` | `201` `DealRead` | `404` "Contact not found" (contact not owned); `422` |
| PATCH | `/api/deals/{deal_id}` | Bearer | `DealUpdate` | `200` `DealRead` | `404`; `422` |
| PATCH | `/api/deals/{deal_id}/stage` | Bearer | `{"stage": DealStage}` | `200` `DealRead` | `404`; `422` |
| DELETE | `/api/deals/{deal_id}` | Bearer | - | `204` | `404` |

- `DealStage`: `lead`, `qualified`, `proposal`, `negotiation`, `closed_won`, `closed_lost`.
  `DealStatus`: `active`, `won`, `lost`.
- `DealCreate`: `title` (1-255, required), `contact_id` (optional, must be owned), `value` (>= 0, 2 dp, default 0),
  `stage` (default `lead`), `status` (default `active`), `expected_close` (date), `notes` (max 5000).
- `DealUpdate`: all optional; `title`, `value`, `stage`, `status`, `notes` reject `null`.
- `/stage` sets `status` to `won` for `closed_won` and `lost` for `closed_lost`; otherwise status is unchanged.
- `DealRead`: `{id, user_id, contact_id, title, value (number), stage, status, expected_close, notes, created_at, updated_at}`.

## Activities (`/api/activities/`)

| Method | Path | Auth | Body | Success | Errors |
|---|---|---|---|---|---|
| GET | `/api/activities/` | Bearer | query: `skip`, `limit`, `contact_id`, `deal_id` | `200` paged `ActivityRead`, by `occurred_at` desc | `401` |
| GET | `/api/activities/{activity_id}` | Bearer | - | `200` `ActivityRead` | `404` "Activity not found" |
| POST | `/api/activities/` | Bearer | `ActivityCreate` | `201` `ActivityRead` | `404` "Contact not found" / "Deal not found"; `422` |
| DELETE | `/api/activities/{activity_id}` | Bearer | - | `204` | `404` |

- `ActivityCreate`: `contact_id`, `deal_id` (optional, must be owned), `type` (`call`, `email`, `meeting`,
  `note` default, `task`), `description` (1-5000), `occurred_at` (required).
- No update endpoint.

## Pipeline stages (`/api/pipeline-stages/`)

| Method | Path | Auth | Body | Success | Errors |
|---|---|---|---|---|---|
| GET | `/api/pipeline-stages/` | Bearer | - | `200` `{total, items}` ordered by `position` (not paged) | `401` |
| GET | `/api/pipeline-stages/{stage_id}` | Bearer | - | `200` `PipelineStageRead` | `404` "Pipeline stage not found" |
| POST | `/api/pipeline-stages/` | Bearer | `{name (1-100), position (0-1000, default 0)}` | `201` `PipelineStageRead` | `409` duplicate name; `422` |
| PATCH | `/api/pipeline-stages/{stage_id}` | Bearer | `{name?, position?}` | `200` `PipelineStageRead` | `404`; `422` |
| DELETE | `/api/pipeline-stages/{stage_id}` | Bearer | - | `204` | `404` |

`PipelineStageRead`: `{id, user_id, name, position, created_at}`. Names are unique per user.

## Analytics (`/api/analytics`)

| Method | Path | Auth | Success |
|---|---|---|---|
| GET | `/api/analytics/summary` | Bearer | `{contacts, deals, activities, pipeline_value, won_value}` (values are status `active` and `won` sums) |
| GET | `/api/analytics/win-rate` | Bearer | `{stages: {stage: count}, win_rate (0-100, 1 dp), won, lost}` |
| GET | `/api/analytics/forecast` | Bearer | `{forecast, breakdown: {stage: {raw, weight, weighted}}}` over active deals |

Forecast weights: lead 0.1, qualified 0.25, proposal 0.5, negotiation 0.75, closed_won 1.0, closed_lost 0.0.

## AI (`/api/ai`)

| Method | Path | Auth | Rate limit | Success | Errors |
|---|---|---|---|---|---|
| GET | `/api/ai/health` | Bearer | - | `200` `{provider, keys, pool}` | `401` |
| GET | `/api/ai/score/{contact_id}` | Bearer | - | `200` `{contact_id, score, label}` | `404` "Contact not found" |
| POST | `/api/ai/insights` | Bearer | 10 per hour per user | `200` `{insights: [str], generated_by}` | `401`, `429` |

- `/api/ai/health`: `provider` is `groq` or `bedrock`; `keys` is the configured key count. `pool` lists per key
  id (8 hex characters, never the secret) and per model: `state` (`ready`, `cooling`, `disabled`),
  `cooldown_s`, `remaining_tokens`, `remaining_requests`, `calls`, `rate_limited`. State is per process.
- `/api/ai/score/{id}`: `score` is the top-class probability x 100 (int). `label` is the model's class.
  With no model file, `{"score": 0, "label": "unknown"}`.
- `/api/ai/insights`: up to 3 lines. `generated_by` is `"ai"` or `"fallback"` (the model id is never returned).
  The endpoint calls the LLM with the smart model (`GROQ_MODEL_SMART`). Any failure, including no key
  configured, returns the deterministic fallback with `generated_by: "fallback"`.

## Chat (`/api/chat`)

| Method | Path | Auth | Rate limit | Body | Success | Errors |
|---|---|---|---|---|---|---|
| GET | `/api/chat/sessions` | Bearer | - | query: `skip`, `limit` (1-100, default 20) | `200` `[ChatSessionRead]` by `updated_at` desc | `401` |
| POST | `/api/chat/sessions` | Bearer | - | - | `201` `ChatSessionRead` (title `New Chat`) | `401` |
| GET | `/api/chat/sessions/{session_id}` | Bearer | - | - | `200` `ChatSessionDetail` | `404` "Chat session not found" |
| DELETE | `/api/chat/sessions/{session_id}` | Bearer | - | - | `204` (also clears the Redis context) | `404` |
| POST | `/api/chat/sessions/{session_id}/message` | Bearer | 30 per 60 s per user | `{"message": str (1-2000)}` | `200` `ChatSendResponse` | `404`; `409` "Still answering your previous message in this chat"; `429` |
| PATCH | `/api/chat/sessions/{session_id}/title` | Bearer | - | `{"title": str (1-100)}` | `200` `ChatSessionRead` | `404`; `422` |

- `ChatSessionRead`: `{id, title, status, created_at, updated_at, message_count}`.
- `ChatSessionDetail`: `ChatSessionRead` plus `messages: [{id, session_id, role, content, intent, created_at}]`.
- `ChatSendResponse`: `{session_id, user_message, ai_message, session_state, intent, extracted_data,
  missing_fields, ready_to_save, confirmation, session_title}`.
  - `session_state`: one of `IDLE`, `CLASSIFYING`, `COLLECTING`, `CONFIRMING`, `SAVING`, `COMPLETE`.
  - `confirmation`: `{intent, entity_type, data, message}`. Present only on the response that enters `SAVING`.
  - When a record is written, the same request also publishes `entity_created` and `dashboard_update` over WebSocket.
- Records are written only after the user's confirming reply. A reply that contains a negation ("no", "don't",
  "but", "change") never saves. There is no separate confirm endpoint yet.

## Appointments (`/api/appointments`)

Router-wide rate limit: 120 per 60 s per user (all verbs).

| Method | Path | Auth | Body | Success | Errors |
|---|---|---|---|---|---|
| GET | `/api/appointments` | Bearer | query: `from`, `to` (aware datetimes), `status` | `200` `[AppointmentRead]` by `starts_at` (not paged) | `401`, `422` |
| POST | `/api/appointments` | Bearer | `AppointmentCreate` | `201` `AppointmentRead` | `404` "Contact not found"; `422` |
| PATCH | `/api/appointments/{appointment_id}` | Bearer | `AppointmentUpdate` | `200` `AppointmentRead` | `404` "Appointment not found"; `422` |

- `AppointmentCreate`: `contact_id` (owned), `starts_at` (aware), `fee_inr` (>= 0, 2 dp), `notes` (max 500).
- `AppointmentUpdate`: `starts_at?`, `fee_inr?`, `status?`, `notes?`; `null` rejected.
- `status`: `booked`, `confirmed`, `completed`, `no_show`, `cancelled`, `rescheduled`.
- `AppointmentRead`: `{id, user_id, contact_id, contact_name, starts_at, fee_inr, status, notes, created_at, updated_at}`.
- No delete endpoint.

## Follow-ups (`/api/follow-ups`)

Router-wide rate limit: 120 per 60 s per user.

| Method | Path | Auth | Body | Success | Errors |
|---|---|---|---|---|---|
| GET | `/api/follow-ups` | Bearer | query: `status` (`pending`, `done`, `skipped`), `due_before` (aware datetime) | `200` `[FollowUpRead]` by `due_at` | `401`, `422` |
| POST | `/api/follow-ups/{task_id}/draft` | Bearer | - | `200` `FollowUpRead` with `draft_en`, `draft_ta` | `404` "FollowUpTask not found"; `409` "Only pending tasks can be drafted" |
| POST | `/api/follow-ups/{task_id}/approve` | Bearer | `{"language": "en" \| "ta", "body": str (1-1000)?}` | `200` `ApproveResponse` | `404`; `409` no draft in that language or task not pending |
| POST | `/api/follow-ups/{task_id}/skip` | Bearer | - | `200` `FollowUpRead` (status `skipped`) | `404`; `409` task not pending |

`404` detail for a missing or foreign id is `"<Model> not found"` (`FollowUpTask`, `Contact`, `Appointment`, `Deal`).

- `FollowUpRead`: `{id, user_id, contact_id, appointment_id, reason, due_at, status, draft_en, draft_ta,
  channel, created_at, contact_name, contact_phone}`.
  `reason`: `reminder_24h`, `reminder_2h`, `no_show_recovery`, `lead_followup`, `manual`.
  `channel` is always `simulated`.
- `/draft` calls the LLM with the message purpose and the IST appointment time only (no name, no phone). Any
  failure returns the built-in English and Tamil templates.
- `/approve`: `body` overrides the draft. It uses the draft in `language` when `body` is absent. The task moves to
  `done` in one conditional update, so a second approve gets `409`. It writes an `outbound_messages` row with
  `status: "sent"` on the simulated channel. Nothing leaves the app.
- `ApproveResponse`: `{task: FollowUpRead, message: {id, user_id, task_id, contact_id, channel, language, body, status, created_at}}`.

## Recovery (`/api/recovery`)

Router-wide rate limit: 30 per 60 s per user.

| Method | Path | Auth | Success | Errors |
|---|---|---|---|---|
| POST | `/api/recovery/run` | Bearer | `200` `{"created": int}` (new tasks only) | `401`, `429` |
| GET | `/api/recovery/summary` | Bearer | `200` `RecoverySummary` (query `days`, 1-365, default 30) | `401`, `422` |

- `POST /run` marks past open appointments (`booked`, `confirmed`) older than 1 h as `no_show` and creates
  reminder tasks for upcoming ones. It is idempotent per (appointment, reason).
- `RecoverySummary`: `{appointments, no_shows, no_show_rate (0-1), pending_tasks, messages_sent,
  recovered_inr (string Decimal), recovered_count}`. `recovered_*` is attribution, not proof of cause. See
  `docs/architecture.md` section 12 for the rule.

## Demo (`/api/demo`)

Router-wide rate limit: 5 per hour per user.

| Method | Path | Auth | Success | Errors |
|---|---|---|---|---|
| POST | `/api/demo/seed` | Bearer | `200` `{contacts, appointments}` (counts added) | `401`, `429` |

Idempotent per demo patient email. The same logic runs from `python -m app.cli seed-demo --email <address>`.

## Real-time (`/api/ws`, `/ws`)

### Ticket (HTTP)

| Method | Path | Auth | Body | Success | Errors |
|---|---|---|---|---|---|
| POST | `/api/ws/ticket` | Bearer | `{"channel": "dashboard"}` or `{"channel": "chat", "session_id": UUID}` | `200` `{"ticket": str, "expires_in": 30}` | `404` "Chat session not found" (not the caller's); `401`; `422` |

A ticket is single-use and expires after 30 s. Chat tickets are issued only for a session the caller owns.

### Sockets

| Path | Query | Server events |
|---|---|---|
| `/ws/dashboard/{user_id}` | `ticket` (dashboard channel) | `dashboard_update` `{type, data}`, `entity_created` `{type, entity_type, entity_id, data}` |
| `/ws/chat/{session_id}` | `ticket` (chat channel, same session) | `ai_typing` `{type, is_typing}` |

- Client text `ping` gets `pong`. Any other text is ignored.
- `user_id` in the path must equal the ticket's user. Otherwise the socket closes `4003`.
- Close codes: `4001` no ticket; `4002` unknown, used or expired ticket; `4003` wrong channel, user or session;
  `4029` the user already has 5 open sockets.
- nginx proxies `/ws/` with Upgrade headers and a 3600 s read timeout.
- Events are pushed by the chat save path only. Other mutations do not push.

## Routes not present

No endpoints exist for: account deletion or data export (SEC-29), logout or token revocation, activity
updates, appointment deletion, leads or inbound webhooks, sending messages to a patient, consents, an audit
log, or a chat confirm endpoint.

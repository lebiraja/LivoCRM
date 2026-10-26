# 10 - Phase 2/3 contract (lean scope)

Purpose: the exact data model and API that the clinic follow-up engine (backend) and the Ledger UI (frontend) share, so both can be built in parallel. Date: 2026-10-26. Status: approved scope cut (see `00-master-plan.md`).

**Scope cuts vs the master plan (deliberate, for speed):** ownership stays `user_id` (no workspaces/roles), the recovery engine runs from an endpoint plus an optional in-process scheduler (no separate worker container), channels are simulated only, no voice notes/PWA/CSV import.

## Data model (Alembic 0010, continue numbering after the latest revision)

| Table | Columns |
|---|---|
| `appointments` | `id uuid pk`, `user_id fk users (cascade)`, `contact_id fk contacts (cascade)`, `starts_at timestamptz`, `fee_inr numeric(10,2) >= 0`, `status` CHECK in `booked, confirmed, completed, no_show, cancelled, rescheduled` (default `booked`), `notes text(500)`, `created_at`, `updated_at`; index `(user_id, starts_at)` |
| `follow_up_tasks` | `id uuid pk`, `user_id`, `contact_id`, `appointment_id fk nullable`, `reason` CHECK in `reminder_24h, reminder_2h, no_show_recovery, lead_followup, manual`, `due_at timestamptz`, `status` CHECK in `pending, done, skipped` (default `pending`), `draft_en text`, `draft_ta text`, `channel` default `simulated`, `created_at`; UNIQUE `(appointment_id, reason)` (idempotent generation); index `(user_id, status, due_at)` |
| `outbound_messages` | `id uuid pk`, `user_id`, `task_id fk`, `contact_id`, `channel`, `language` (`en`/`ta`), `body text`, `status` default `sent`, `created_at` |

All money is `Decimal`. All writes verify ownership with `app/services/ownership.py::require_owned`. Times are stored UTC; the UI shows IST.

## API (all under `/api`, Bearer JWT, rate limited, 404 for another user's rows)

| Method + path | Body / query | Response |
|---|---|---|
| `GET /appointments` | `?from=&to=&status=` | `[Appointment]` |
| `POST /appointments` | `{contact_id, starts_at, fee_inr, notes?}` | `201 Appointment` |
| `PATCH /appointments/{id}` | any of `starts_at, fee_inr, status, notes` | `Appointment` |
| `GET /follow-ups` | `?status=pending&due_before=` | `[FollowUp]` (with `contact_name`, `contact_phone`) |
| `POST /follow-ups/{id}/draft` | `{}` | `FollowUp` with `draft_en`, `draft_ta` filled (Groq via `chat_completion`; deterministic template fallback when the LLM fails) |
| `POST /follow-ups/{id}/approve` | `{language: "en"\|"ta", body?}` | `{task, message}`: task `done`, one `outbound_messages` row, no external send |
| `POST /follow-ups/{id}/skip` | `{}` | `FollowUp` status `skipped` |
| `POST /recovery/run` | `{}` | `{created: int}`: idempotently creates tasks: `reminder_24h` when an open appointment starts within 24 h, `reminder_2h` within 2 h, `no_show_recovery` for `booked/confirmed` appointments whose start passed more than 1 h ago (also flips them to `no_show`) |
| `GET /recovery/summary` | `?days=30` | `{appointments, no_shows, no_show_rate, pending_tasks, messages_sent, recovered_inr, recovered_count}`; `recovered_*` = fee of `completed` appointments created after an approved `no_show_recovery` message for the same contact (attributed, not causal) |
| `POST /demo/seed` | `{}` | `{contacts, appointments}`: idempotent clinic demo data (Tamil and English names, past/future appointments); the same logic is exposed as `python -m app.cli seed-demo` |

Optional in-process scheduler: when `ENABLE_SCHEDULER=true`, a lifespan task calls the same generator every 60 s per user with open appointments (default off; tests never enable it).

## Frontend (Ledger, lean)

Warm paper `#F6F1E7`, ink `#1B1A17`, one deep-green accent `#1F5D45`, serif headings (system serif stack is fine; fonts are self-hosted already), ruled rows instead of card grids, mobile bottom nav under 768 px, EN/TA toggle (catalogue in `src/i18n/`), `formatINR` everywhere. Screens: **Today** (home: pending follow-ups as ruled rows with Draft / Approve / Skip, KPI line from `/recovery/summary`), **Appointments** (list + create + mark completed/no-show), Leads/Contacts, Pipeline, Assistant, Reports (recovered ₹, no-show rate), Settings (AI key-pool health from `GET /ai/health`, language). Dark mode must work (tokens for both themes). Tamil strings must never truncate (wrap, no fixed widths).

## Definition of done per piece

Backend: migration up/down tested, every endpoint has success + 404-other-user + invalid-input tests, `pytest` green with coverage not below the current 81%. Frontend: `tsc -b`, eslint, `npm run build`, vitest green; Today, Appointments and the language toggle have tests. Update `FIXES.md`/`STATUS.md` only via the lead.

"""Recovery engine: turns appointment state into follow-up tasks and reports what came back.

Every rule takes an explicit `now`, so tests and the scheduler share one clock.
Generation is idempotent: the unique (appointment_id, reason) constraint absorbs repeats.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.appointment import Appointment
from app.models.follow_up import FollowUpTask
from app.models.outbound_message import OutboundMessage
from app.schemas.recovery import RecoverySummary

logger = logging.getLogger(__name__)

OPEN_STATUSES = ("booked", "confirmed")
NO_SHOW_GRACE = timedelta(hours=1)
# (reason, how long before the start the reminder is due)
REMINDERS: tuple[tuple[str, timedelta], ...] = (
    ("reminder_24h", timedelta(hours=24)),
    ("reminder_2h", timedelta(hours=2)),
)
SCHEDULER_TICK_SECONDS = 60


async def generate_recovery_tasks(db: AsyncSession, user_id: UUID, now: datetime) -> int:
    """Create the due tasks for one user's open appointments and return how many were new."""
    open_appointments = select(Appointment).where(
        Appointment.user_id == user_id, Appointment.status.in_(OPEN_STATUSES)
    )
    rows: list[dict[str, Any]] = []

    for appt in (await db.scalars(open_appointments.where(Appointment.starts_at < now - NO_SHOW_GRACE))).all():
        appt.status = "no_show"
        rows.append(
            {
                "user_id": user_id,
                "contact_id": appt.contact_id,
                "appointment_id": appt.id,
                "reason": "no_show_recovery",
                "due_at": now,
            }
        )

    for appt in (await db.scalars(open_appointments.where(Appointment.starts_at > now))).all():
        for reason, lead in REMINDERS:
            due_at = appt.starts_at - lead
            if due_at <= now:
                rows.append(
                    {
                        "user_id": user_id,
                        "contact_id": appt.contact_id,
                        "appointment_id": appt.id,
                        "reason": reason,
                        "due_at": due_at,
                    }
                )

    created = 0
    if rows:
        inserted = await db.execute(
            pg_insert(FollowUpTask)
            .values(rows)
            .on_conflict_do_nothing(constraint="uq_follow_up_tasks_appointment_reason")
            .returning(FollowUpTask.id)
        )
        created = len(inserted.all())
    await db.commit()
    return created


async def generate_for_open_users(db: AsyncSession, now: datetime) -> int:
    """Scheduler tick: run the generator for every user that has an open appointment."""
    user_ids = (
        await db.scalars(select(Appointment.user_id).where(Appointment.status.in_(OPEN_STATUSES)).distinct())
    ).all()
    total = 0
    for user_id in user_ids:
        total += await generate_recovery_tasks(db, user_id, now)
    return total


async def summarize_recovery(db: AsyncSession, user_id: UUID, now: datetime, days: int) -> RecoverySummary:
    """KPIs for the last `days` days of appointments.

    `recovered_*` attributes revenue to recovery work: completed visits, created after an approved
    no_show_recovery message to the same patient. It is attribution, not proof of causation.
    """
    since = now - timedelta(days=days)
    in_window = (Appointment.user_id == user_id, Appointment.starts_at >= since, Appointment.starts_at <= now)

    appointments, no_shows = (
        await db.execute(
            select(func.count(), func.count().filter(Appointment.status == "no_show")).where(*in_window)
        )
    ).one()

    approved_recovery = (
        select(OutboundMessage.id)
        .join(FollowUpTask, FollowUpTask.id == OutboundMessage.task_id)
        .where(
            OutboundMessage.user_id == user_id,
            OutboundMessage.contact_id == Appointment.contact_id,
            OutboundMessage.created_at < Appointment.created_at,
            FollowUpTask.reason == "no_show_recovery",
        )
        .exists()
    )
    recovered_inr, recovered_count = (
        await db.execute(
            select(func.coalesce(func.sum(Appointment.fee_inr), 0), func.count()).where(
                *in_window, Appointment.status == "completed", approved_recovery
            )
        )
    ).one()

    pending = await db.scalar(
        select(func.count())
        .select_from(FollowUpTask)
        .where(FollowUpTask.user_id == user_id, FollowUpTask.status == "pending")
    )
    messages_sent = await db.scalar(
        select(func.count())
        .select_from(OutboundMessage)
        .where(OutboundMessage.user_id == user_id, OutboundMessage.created_at >= since)
    )

    return RecoverySummary(
        appointments=appointments,
        no_shows=no_shows,
        no_show_rate=round(no_shows / appointments, 4) if appointments else 0.0,
        pending_tasks=pending or 0,
        messages_sent=messages_sent or 0,
        recovered_inr=recovered_inr,
        recovered_count=recovered_count,
    )


async def run_scheduler() -> None:
    """Background loop started by the lifespan when ENABLE_SCHEDULER is on; cancelled at shutdown."""
    while True:
        await asyncio.sleep(SCHEDULER_TICK_SECONDS)
        try:
            async with async_session_factory() as db:
                created = await generate_for_open_users(db, datetime.now(UTC))
        except Exception:
            # A failed tick must not end the loop; the next tick retries
            logger.exception("Recovery scheduler tick failed")
            continue
        if created:
            logger.info("Recovery scheduler created %d follow-up tasks", created)

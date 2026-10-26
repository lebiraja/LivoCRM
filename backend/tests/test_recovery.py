"""Recovery engine: 24 h / 2 h / no-show rules with a fixed clock, idempotency, summary math, endpoints."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.contact import Contact
from app.models.follow_up import FollowUpTask
from app.models.outbound_message import OutboundMessage
from app.models.user import User
from app.services.recovery import generate_for_open_users, generate_recovery_tasks, summarize_recovery
from tests.conftest import auth_headers

NOW = datetime(2026, 10, 27, 4, 30, tzinfo=UTC)  # 10:00 IST


async def _reasons(db: AsyncSession, user: User) -> list[str]:
    rows = await db.scalars(select(FollowUpTask.reason).where(FollowUpTask.user_id == user.id))
    return sorted(rows.all())


async def _appointment(
    db: AsyncSession,
    user: User,
    contact: Contact,
    starts_at: datetime,
    status: str = "booked",
    fee_inr: Decimal = Decimal("300"),
    created_at: datetime | None = None,
) -> Appointment:
    appt = Appointment(user_id=user.id, contact_id=contact.id, starts_at=starts_at, fee_inr=fee_inr, status=status)
    if created_at is not None:
        appt.created_at = created_at
    db.add(appt)
    await db.commit()
    return appt


@pytest.fixture
async def clinic(db: AsyncSession, make_user: Callable[..., Awaitable[User]]) -> dict[str, Any]:
    user = await make_user()
    other = await make_user()
    patient = Contact(user_id=user.id, name="Meena", phone="+919000000010")
    other_patient = Contact(user_id=other.id, name="Ravi", phone="+919000000011")
    db.add_all([patient, other_patient])
    await db.commit()
    return {"user": user, "other": other, "patient": patient, "other_patient": other_patient}


# ── Generation rules (service level, injected clock) ────────────────────────


async def test_reminder_24h_fires_inside_24_hours_only(db: AsyncSession, clinic: dict[str, Any]) -> None:
    await _appointment(db, clinic["user"], clinic["patient"], NOW + timedelta(hours=20))
    await _appointment(db, clinic["user"], clinic["patient"], NOW + timedelta(hours=30))

    created = await generate_recovery_tasks(db, clinic["user"].id, NOW)

    assert created == 1
    assert await _reasons(db, clinic["user"]) == ["reminder_24h"]


async def test_reminder_2h_fires_inside_2_hours(db: AsyncSession, clinic: dict[str, Any]) -> None:
    await _appointment(db, clinic["user"], clinic["patient"], NOW + timedelta(hours=1))

    created = await generate_recovery_tasks(db, clinic["user"].id, NOW)

    assert created == 2
    assert await _reasons(db, clinic["user"]) == ["reminder_24h", "reminder_2h"]


async def test_reminder_2h_not_yet_due_at_three_hours(db: AsyncSession, clinic: dict[str, Any]) -> None:
    await _appointment(db, clinic["user"], clinic["patient"], NOW + timedelta(hours=3))

    await generate_recovery_tasks(db, clinic["user"].id, NOW)

    assert await _reasons(db, clinic["user"]) == ["reminder_24h"]


async def test_reminder_due_times_follow_the_appointment(db: AsyncSession, clinic: dict[str, Any]) -> None:
    starts = NOW + timedelta(hours=1)
    await _appointment(db, clinic["user"], clinic["patient"], starts)

    await generate_recovery_tasks(db, clinic["user"].id, NOW)

    due = dict(
        (await db.execute(select(FollowUpTask.reason, FollowUpTask.due_at).where(FollowUpTask.user_id == clinic["user"].id))).all()
    )
    assert due["reminder_24h"] == starts - timedelta(hours=24)
    assert due["reminder_2h"] == starts - timedelta(hours=2)


async def test_no_show_after_one_hour_grace_flips_status_and_creates_task(
    db: AsyncSession, clinic: dict[str, Any]
) -> None:
    appt = await _appointment(db, clinic["user"], clinic["patient"], NOW - timedelta(minutes=61))

    created = await generate_recovery_tasks(db, clinic["user"].id, NOW)

    await db.refresh(appt)
    assert created == 1
    assert appt.status == "no_show"
    assert await _reasons(db, clinic["user"]) == ["no_show_recovery"]


async def test_no_show_inside_grace_window_is_untouched(db: AsyncSession, clinic: dict[str, Any]) -> None:
    appt = await _appointment(db, clinic["user"], clinic["patient"], NOW - timedelta(minutes=59))

    created = await generate_recovery_tasks(db, clinic["user"].id, NOW)

    await db.refresh(appt)
    assert created == 0
    assert appt.status == "booked"


async def test_closed_statuses_never_generate_tasks(db: AsyncSession, clinic: dict[str, Any]) -> None:
    await _appointment(db, clinic["user"], clinic["patient"], NOW + timedelta(hours=1), status="cancelled")
    await _appointment(db, clinic["user"], clinic["patient"], NOW - timedelta(hours=5), status="completed")

    created = await generate_recovery_tasks(db, clinic["user"].id, NOW)

    assert created == 0


async def test_second_run_creates_nothing(db: AsyncSession, clinic: dict[str, Any]) -> None:
    await _appointment(db, clinic["user"], clinic["patient"], NOW + timedelta(hours=1))
    await _appointment(db, clinic["user"], clinic["patient"], NOW - timedelta(hours=2))

    first = await generate_recovery_tasks(db, clinic["user"].id, NOW)
    second = await generate_recovery_tasks(db, clinic["user"].id, NOW)

    assert first == 3
    assert second == 0
    assert len(await _reasons(db, clinic["user"])) == 3


async def test_run_never_touches_another_users_appointments(db: AsyncSession, clinic: dict[str, Any]) -> None:
    await _appointment(db, clinic["other"], clinic["other_patient"], NOW - timedelta(hours=3))

    created = await generate_recovery_tasks(db, clinic["user"].id, NOW)

    assert created == 0
    assert await _reasons(db, clinic["other"]) == []


async def test_scheduler_tick_covers_every_user_with_open_appointments(db: AsyncSession, clinic: dict[str, Any]) -> None:
    await _appointment(db, clinic["user"], clinic["patient"], NOW + timedelta(hours=1))
    await _appointment(db, clinic["other"], clinic["other_patient"], NOW - timedelta(hours=3))

    created = await generate_for_open_users(db, NOW)
    again = await generate_for_open_users(db, NOW)

    assert created == 3
    assert again == 0


# ── Summary math ────────────────────────────────────────────────────────────


async def test_summary_counts_and_attributes_recovered_revenue(
    db: AsyncSession, clinic: dict[str, Any]
) -> None:
    user, pa = clinic["user"], clinic["patient"]
    patient_b = Contact(user_id=user.id, name="Kumar", phone="+919000000012")
    patient_c = Contact(user_id=user.id, name="Priya", phone="+919000000013")
    patient_d = Contact(user_id=user.id, name="Selvi", phone="+919000000014")
    patient_e = Contact(user_id=user.id, name="Vijay", phone="+919000000015")
    db.add_all([patient_b, patient_c, patient_d, patient_e])
    await db.commit()

    async def task_for(appt: Appointment | None, reason: str, status: str, contact: Contact) -> FollowUpTask:
        row = FollowUpTask(
            user_id=user.id, contact_id=contact.id, appointment_id=appt.id if appt else None,
            reason=reason, due_at=NOW, status=status,
        )
        db.add(row)
        await db.flush()
        return row

    async def message_for(row: FollowUpTask, contact: Contact, sent_at: datetime) -> None:
        db.add(
            OutboundMessage(
                user_id=user.id, task_id=row.id, contact_id=contact.id, channel="simulated",
                language="en", body="Hello", status="sent", created_at=sent_at,
            )
        )
        await db.flush()

    # Patient A: two no-shows, both recovery messages approved; the rebooking is attributed once
    a_ns1 = await _appointment(db, user, pa, NOW - timedelta(days=2), "no_show", created_at=NOW - timedelta(days=3))
    a_ns2 = await _appointment(db, user, pa, NOW - timedelta(days=7), "no_show", created_at=NOW - timedelta(days=8))
    t_a1 = await task_for(a_ns1, "no_show_recovery", "done", pa)
    t_a2 = await task_for(a_ns2, "no_show_recovery", "done", pa)
    await message_for(t_a1, pa, NOW - timedelta(days=1))
    await message_for(t_a2, pa, NOW - timedelta(days=6))
    await _appointment(
        db, user, pa, NOW - timedelta(hours=10), "completed",
        fee_inr=Decimal("1000.00"), created_at=NOW - timedelta(hours=12),
    )

    # Patient B: a completed visit with no message at all, plus a no-show
    await _appointment(db, user, patient_b, NOW - timedelta(days=5), "completed", created_at=NOW - timedelta(days=6))
    await _appointment(db, user, patient_b, NOW - timedelta(days=4), "no_show", created_at=NOW - timedelta(days=5))

    # Patient C: the visit was created BEFORE the recovery message, so it is not attributed
    c_ns = await _appointment(db, user, patient_c, NOW - timedelta(days=3), "no_show", created_at=NOW - timedelta(days=4))
    t_c = await task_for(c_ns, "no_show_recovery", "done", patient_c)
    await message_for(t_c, patient_c, NOW - timedelta(days=2))
    await _appointment(
        db, user, patient_c, NOW - timedelta(days=1), "completed",
        fee_inr=Decimal("700"), created_at=NOW - timedelta(days=3),
    )

    # Patient D: a message for a 24 h reminder, not a recovery, so not attributed
    d_appt = await _appointment(
        db, user, patient_d, NOW - timedelta(days=2), "completed",
        fee_inr=Decimal("800"), created_at=NOW - timedelta(days=4),
    )
    t_d = await task_for(d_appt, "reminder_24h", "done", patient_d)
    await message_for(t_d, patient_d, NOW - timedelta(days=3))

    # Outside the 30-day window: an old recovery message and an old completed visit
    e_appt = await _appointment(
        db, user, patient_e, NOW - timedelta(days=35), "completed",
        fee_inr=Decimal("9999"), created_at=NOW - timedelta(days=36),
    )
    t_e = await task_for(e_appt, "no_show_recovery", "done", patient_e)
    await message_for(t_e, patient_e, NOW - timedelta(days=38))

    # Open work: one pending manual task counts; a skipped one does not
    await task_for(None, "manual", "pending", patient_e)
    await task_for(None, "manual", "skipped", patient_e)
    await db.commit()

    summary = await summarize_recovery(db, user.id, NOW, days=30)

    assert summary.appointments == 8
    assert summary.no_shows == 4
    assert summary.no_show_rate == 0.5
    assert summary.pending_tasks == 1
    assert summary.messages_sent == 4
    assert summary.recovered_count == 1
    assert summary.recovered_inr == Decimal("1000.00")


async def test_summary_rate_is_zero_without_appointments(db: AsyncSession, clinic: dict[str, Any]) -> None:
    summary = await summarize_recovery(db, clinic["user"].id, NOW, days=30)

    assert summary.appointments == 0
    assert summary.no_show_rate == 0.0
    assert summary.recovered_inr == Decimal("0")
    assert summary.recovered_count == 0


# ── Endpoints ───────────────────────────────────────────────────────────────


async def test_run_endpoint_creates_tasks_then_none(client: AsyncClient, db: AsyncSession, clinic: dict[str, Any]) -> None:
    soon = datetime.now(UTC) + timedelta(hours=1)
    await _appointment(db, clinic["user"], clinic["patient"], soon)
    headers = auth_headers(clinic["user"])

    first = await client.post("/api/recovery/run", json={}, headers=headers)
    second = await client.post("/api/recovery/run", json={}, headers=headers)

    assert first.status_code == 200
    assert first.json() == {"created": 2}
    assert second.json() == {"created": 0}


async def test_run_endpoint_ignores_other_users(client: AsyncClient, db: AsyncSession, clinic: dict[str, Any]) -> None:
    await _appointment(db, clinic["other"], clinic["other_patient"], datetime.now(UTC) + timedelta(hours=1))

    response = await client.post("/api/recovery/run", json={}, headers=auth_headers(clinic["user"]))

    assert response.json() == {"created": 0}


async def test_summary_endpoint_shape(client: AsyncClient, clinic: dict[str, Any]) -> None:
    response = await client.get("/api/recovery/summary", params={"days": 7}, headers=auth_headers(clinic["user"]))

    assert response.status_code == 200
    assert set(response.json()) == {
        "appointments", "no_shows", "no_show_rate", "pending_tasks",
        "messages_sent", "recovered_inr", "recovered_count",
    }


@pytest.mark.parametrize("query", [{"days": 0}, {"days": 366}, {"days": "many"}])
async def test_summary_rejects_invalid_days(client: AsyncClient, clinic: dict[str, Any], query: dict[str, str]) -> None:
    response = await client.get("/api/recovery/summary", params=query, headers=auth_headers(clinic["user"]))

    assert response.status_code == 422


async def test_summary_scoped_to_callers_clinic(client: AsyncClient, db: AsyncSession, clinic: dict[str, Any]) -> None:
    await _appointment(db, clinic["other"], clinic["other_patient"], datetime.now(UTC) - timedelta(days=1), "no_show")

    response = await client.get("/api/recovery/summary", headers=auth_headers(clinic["user"]))

    assert response.json()["no_shows"] == 0

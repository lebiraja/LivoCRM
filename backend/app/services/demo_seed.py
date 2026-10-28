"""Clinic demo data: English-named patients with past and future visits, pipeline deals across
all six stages and activities, all labelled DEMO.

Idempotent per patient: a patient is added only when this user has no demo contact with that
email yet, so running the seed again adds nothing.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.appointment import Appointment
from app.models.contact import Contact
from app.models.deal import Deal
from app.schemas.recovery import DemoSeedResponse

IST = timezone(timedelta(hours=5, minutes=30), "IST")
DEMO_DOMAIN = "demo.livocrm.test"
DEMO_COMPANY = "Demo Clinic, Coimbatore"

DEMO_PATIENTS: tuple[str, ...] = (
    "Murugan Raj",
    "Meena Subramanian",
    "Lakshmi Narayan",
    "Arun Kumar",
    "Karthik Velu",
    "Priya Nair",
    "Selvi Dharan",
    "Vijay Raman",
    "Anbu Chelvan",
    "Divya Selvaraj",
    "Ramesh Babu",
    "Kavitha Iyer",
)


# Pipeline stages in order; the 12 demo patients spread two deals over each stage
PIPELINE_STAGES: tuple[str, ...] = (
    "lead",
    "qualified",
    "proposal",
    "negotiation",
    "closed_won",
    "closed_lost",
)
DEAL_TITLES: tuple[str, ...] = (
    "Dental scaling and polishing",
    "Root canal treatment",
    "Annual health check package",
    "Orthodontic braces plan",
    "Diabetes care programme",
    "Physiotherapy 10-session pack",
)
DEAL_VALUES: tuple[int, ...] = (1800, 6500, 4200, 38000, 9600, 7500, 2400, 15000)
ACTIVITY_NOTES: tuple[tuple[str, str], ...] = (
    ("call", "DEMO: called to confirm interest in the treatment plan"),
    ("note", "DEMO: asked about payment options and appointment timing"),
    ("meeting", "DEMO: consultation at the clinic"),
    ("email", "DEMO: sent the treatment estimate"),
)


def _deal_for(index: int, now: datetime) -> tuple[str, str, str, Decimal, datetime.date]:
    """(title, stage, status, value, expected_close) for the patient at `index` (1-based)."""
    stage = PIPELINE_STAGES[(index - 1) % len(PIPELINE_STAGES)]
    status = {"closed_won": "won", "closed_lost": "lost"}.get(stage, "active")
    close_offset = -3 - index if status != "active" else 7 + 3 * index
    return (
        DEAL_TITLES[(index - 1) % len(DEAL_TITLES)],
        stage,
        status,
        Decimal(DEAL_VALUES[(index - 1) % len(DEAL_VALUES)]),
        (now + timedelta(days=close_offset)).date(),
    )


async def _seed_pipeline(db: AsyncSession, user_id: UUID, now: datetime) -> tuple[int, int]:
    """Deals and activities for every demo patient that has none yet (idempotent, also fills old seeds)."""
    contacts = (
        await db.scalars(
            select(Contact)
            .where(Contact.user_id == user_id, Contact.email.like(f"%@{DEMO_DOMAIN}"))
            .order_by(Contact.email)
        )
    ).all()
    with_deals = set(
        (await db.scalars(select(Deal.contact_id).where(Deal.user_id == user_id, Deal.notes.like("DEMO%")))).all()
    )
    deals_created = activities_created = 0
    for contact in contacts:
        if contact.id in with_deals:
            continue
        index = int((contact.email or "patient00@")[7:9] or 0) or 1
        title, stage, status, value, close = _deal_for(index, now)
        deal = Deal(
            id=uuid.uuid4(),
            user_id=user_id,
            contact_id=contact.id,
            title=title,
            value=value,
            stage=stage,
            status=status,
            expected_close=close,
            notes="DEMO: seeded pipeline deal",
        )
        db.add(deal)
        await db.flush()
        deals_created += 1
        for step in range(2):
            kind, description = ACTIVITY_NOTES[(index + step) % len(ACTIVITY_NOTES)]
            db.add(
                Activity(
                    user_id=user_id,
                    contact_id=contact.id,
                    deal_id=deal.id,
                    type=kind,
                    description=description,
                    occurred_at=now - timedelta(days=2 + index % 6 + 3 * step),
                )
            )
            activities_created += 1
    return deals_created, activities_created


def _visits(index: int, now: datetime) -> list[tuple[datetime, str, Decimal]]:
    """One past visit (completed or no-show) and one upcoming visit, spread by patient index."""
    today = now.astimezone(IST).replace(hour=0, minute=0, second=0, microsecond=0)
    past = today - timedelta(days=5 + index % 4)
    upcoming = today + timedelta(days=1 + index % 5)
    return [
        (
            past.replace(hour=10),
            "no_show" if index % 3 == 0 else "completed",
            Decimal(300 + 50 * (index % 4)),
        ),
        (upcoming.replace(hour=11), "confirmed" if index % 2 else "booked", Decimal("400.00")),
    ]


async def seed_demo_data(db: AsyncSession, user_id: UUID, now: datetime) -> DemoSeedResponse:
    existing = set(
        (
            await db.scalars(
                select(Contact.email).where(
                    Contact.user_id == user_id, Contact.email.like(f"%@{DEMO_DOMAIN}")
                )
            )
        ).all()
    )

    contacts_created = 0
    appointments_created = 0
    for index, name in enumerate(DEMO_PATIENTS, start=1):
        email = f"patient{index:02d}@{DEMO_DOMAIN}"
        if email in existing:
            continue
        contact = Contact(
            id=uuid.uuid4(),
            user_id=user_id,
            name=name,
            email=email,
            phone=f"+9190000{index:05d}",
            company=DEMO_COMPANY,
            tags=["DEMO"],
            notes="DEMO: seeded clinic data",
        )
        db.add(contact)
        # Flush so the contact row exists before its appointments (no ORM relationship orders them)
        await db.flush()
        contacts_created += 1
        for starts_at, status, fee in _visits(index, now):
            db.add(
                Appointment(
                    user_id=user_id,
                    contact_id=contact.id,
                    starts_at=starts_at,
                    fee_inr=fee,
                    status=status,
                    notes="DEMO",
                )
            )
            appointments_created += 1

    deals_created, activities_created = await _seed_pipeline(db, user_id, now)
    await db.commit()
    return DemoSeedResponse(
        contacts=contacts_created,
        appointments=appointments_created,
        deals=deals_created,
        activities=activities_created,
    )

"""Clinic demo data: Tamil and English patients with past and future visits, all labelled DEMO.

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

from app.models.appointment import Appointment
from app.models.contact import Contact
from app.schemas.recovery import DemoSeedResponse

IST = timezone(timedelta(hours=5, minutes=30), "IST")
DEMO_DOMAIN = "demo.livocrm.test"
DEMO_COMPANY = "Demo Clinic, Coimbatore"

DEMO_PATIENTS: tuple[str, ...] = (
    "முருகன் ராஜ்",
    "Meena Subramanian",
    "லட்சுமி",
    "Arun Kumar",
    "கார்த்திக் வேலு",
    "Priya Nair",
    "செல்வி",
    "Vijay Raman",
    "அன்புச்செல்வன்",
    "Divya Selvaraj",
    "Ramesh Babu",
    "கவிதா",
)


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

    await db.commit()
    return DemoSeedResponse(contacts=contacts_created, appointments=appointments_created)

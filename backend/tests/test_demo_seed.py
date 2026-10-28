"""Demo seed: endpoint and `python -m app.cli seed-demo` are idempotent and cover Tamil and English names."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app import cli
from app.models.appointment import Appointment
from app.models.contact import Contact
from app.models.user import User
from app.schemas.recovery import DemoSeedResponse
from app.services.demo_seed import DEMO_PATIENTS
from tests.conftest import auth_headers

PATIENTS = len(DEMO_PATIENTS)


async def _demo_contacts(db: AsyncSession, user: User) -> list[Contact]:
    return list((await db.scalars(select(Contact).where(Contact.user_id == user.id))).all())


async def test_seed_endpoint_builds_clinic_demo(
    client: AsyncClient, db: AsyncSession, make_user: Callable[..., Awaitable[User]]
) -> None:
    user = await make_user()

    response = await client.post("/api/demo/seed", json={}, headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json() == {"contacts": PATIENTS, "appointments": 2 * PATIENTS, "deals": PATIENTS, "activities": 2 * PATIENTS}
    contacts = await _demo_contacts(db, user)
    names = [contact.name for contact in contacts]
    assert all(name.isascii() for name in names)
    assert all("DEMO" in contact.tags for contact in contacts)
    starts = list((await db.scalars(select(Appointment.starts_at).where(Appointment.user_id == user.id))).all())
    now = datetime.now(UTC)
    assert any(starts_at < now for starts_at in starts)
    assert any(starts_at > now for starts_at in starts)


async def test_seed_endpoint_is_idempotent(
    client: AsyncClient, db: AsyncSession, make_user: Callable[..., Awaitable[User]]
) -> None:
    user = await make_user()
    headers = auth_headers(user)
    await client.post("/api/demo/seed", json={}, headers=headers)

    second = await client.post("/api/demo/seed", json={}, headers=headers)

    assert second.json() == {"contacts": 0, "appointments": 0, "deals": 0, "activities": 0}
    assert len(await _demo_contacts(db, user)) == PATIENTS
    appointments = await db.scalar(select(func.count()).select_from(Appointment).where(Appointment.user_id == user.id))
    assert appointments == 2 * PATIENTS


async def test_seed_is_scoped_per_user(
    client: AsyncClient, db: AsyncSession, make_user: Callable[..., Awaitable[User]]
) -> None:
    first, second = await make_user(), await make_user()
    await client.post("/api/demo/seed", json={}, headers=auth_headers(first))

    response = await client.post("/api/demo/seed", json={}, headers=auth_headers(second))

    assert response.json() == {"contacts": PATIENTS, "appointments": 2 * PATIENTS, "deals": PATIENTS, "activities": 2 * PATIENTS}


@pytest.fixture
def cli_sessions(db_conn: AsyncConnection, monkeypatch: pytest.MonkeyPatch) -> None:
    """The CLI opens its own session; bind it to the test transaction so its rows are visible to the test."""
    monkeypatch.setattr(
        cli,
        "async_session_factory",
        lambda: AsyncSession(bind=db_conn, join_transaction_mode="create_savepoint", expire_on_commit=False),
    )


async def test_cli_seed_is_idempotent(
    db: AsyncSession, make_user: Callable[..., Awaitable[User]], cli_sessions: None
) -> None:
    user = await make_user(email="clinic-owner@example.com")

    first = await cli.seed_demo_for_email("clinic-owner@example.com")
    second = await cli.seed_demo_for_email("clinic-owner@example.com")

    assert first == DemoSeedResponse(contacts=PATIENTS, appointments=2 * PATIENTS, deals=PATIENTS, activities=2 * PATIENTS)
    assert second == DemoSeedResponse(contacts=0, appointments=0, deals=0, activities=0)
    assert len(await _demo_contacts(db, user)) == PATIENTS


async def test_cli_rejects_unknown_email(cli_sessions: None) -> None:
    with pytest.raises(SystemExit):
        await cli.seed_demo_for_email("nobody@example.com")


async def test_seed_fills_every_pipeline_stage_and_is_idempotent(client, db, make_user) -> None:
    from sqlalchemy import func, select

    from app.models.activity import Activity
    from app.models.deal import Deal

    user = await make_user()
    for _ in range(2):
        assert (await client.post("/api/demo/seed", json={}, headers=auth_headers(user))).status_code == 200

    deals = (await db.scalars(select(Deal).where(Deal.user_id == user.id))).all()
    assert len(deals) == PATIENTS
    assert {deal.stage for deal in deals} == {
        "lead", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"
    }
    assert {(deal.stage, deal.status) for deal in deals if deal.stage.startswith("closed")} == {
        ("closed_won", "won"),
        ("closed_lost", "lost"),
    }
    assert all(deal.contact_id is not None and deal.notes.startswith("DEMO") for deal in deals)
    activities = await db.scalar(select(func.count()).select_from(Activity).where(Activity.user_id == user.id))
    assert activities == 2 * PATIENTS
    listed = await client.get("/api/deals/", headers=auth_headers(user))
    assert listed.status_code == 200 and listed.json()["total"] == PATIENTS

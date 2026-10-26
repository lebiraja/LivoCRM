"""Appointments API: success, another user's rows answer 404, bad input answers 422."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.contact import Contact
from app.models.user import User
from tests.conftest import auth_headers

START = datetime(2026, 10, 27, 4, 30, tzinfo=UTC)  # 10:00 IST


@pytest.fixture
async def tenants(db: AsyncSession, make_user: Callable[..., Awaitable[User]]) -> dict[str, Any]:
    """User A owns a contact; user B owns a contact and a booked appointment."""
    a, b = await make_user(), await make_user()
    a_contact = Contact(user_id=a.id, name="A's patient")
    b_contact = Contact(user_id=b.id, name="B's patient")
    db.add_all([a_contact, b_contact])
    await db.commit()
    appt = Appointment(user_id=b.id, contact_id=b_contact.id, starts_at=START, fee_inr=Decimal("300.00"))
    db.add(appt)
    await db.commit()
    return {"a": a, "b": b, "a_contact": str(a_contact.id), "b_contact": str(b_contact.id), "b_appt": str(appt.id)}


async def test_create_appointment_returns_201(client: AsyncClient, tenants: dict[str, Any]) -> None:
    response = await client.post(
        "/api/appointments",
        json={
            "contact_id": tenants["a_contact"],
            "starts_at": "2026-10-28T05:00:00Z",
            "fee_inr": "450.50",
            "notes": "first visit",
        },
        headers=auth_headers(tenants["a"]),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "booked"
    assert body["fee_inr"] == "450.50"
    assert body["contact_id"] == tenants["a_contact"]
    assert body["user_id"] == str(tenants["a"].id)


async def test_create_for_another_users_contact_is_404(client: AsyncClient, tenants: dict[str, Any]) -> None:
    response = await client.post(
        "/api/appointments",
        json={"contact_id": tenants["b_contact"], "starts_at": "2026-10-28T05:00:00Z", "fee_inr": "300"},
        headers=auth_headers(tenants["a"]),
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"starts_at": "2026-10-28T05:00:00", "fee_inr": "300"},  # naive datetime
        {"starts_at": "2026-10-28T05:00:00Z", "fee_inr": "-1"},  # negative fee
        {"starts_at": "2026-10-28T05:00:00Z", "fee_inr": "1.005"},  # more than 2 decimals
        {"starts_at": "2026-10-28T05:00:00Z", "fee_inr": "300", "notes": "x" * 501},
        {"starts_at": "2026-10-28T05:00:00Z", "fee_inr": "300", "contact_id": "not-a-uuid"},
        {"fee_inr": "300"},  # missing starts_at
    ],
)
async def test_create_rejects_invalid_input(client: AsyncClient, tenants: dict[str, Any], payload: dict[str, Any]) -> None:
    body = {"contact_id": tenants["a_contact"], **payload}

    response = await client.post("/api/appointments", json=body, headers=auth_headers(tenants["a"]))

    assert response.status_code == 422


async def test_list_filters_by_range_and_status(client: AsyncClient, tenants: dict[str, Any]) -> None:
    headers = auth_headers(tenants["b"])

    in_range = await client.get(
        "/api/appointments", params={"from": "2026-10-27T00:00:00Z", "to": "2026-10-28T00:00:00Z"}, headers=headers
    )
    after_range = await client.get("/api/appointments", params={"from": "2026-10-28T00:00:00Z"}, headers=headers)
    booked = await client.get("/api/appointments", params={"status": "booked"}, headers=headers)
    completed = await client.get("/api/appointments", params={"status": "completed"}, headers=headers)

    assert [row["id"] for row in in_range.json()] == [tenants["b_appt"]]
    assert after_range.json() == []
    assert [row["id"] for row in booked.json()] == [tenants["b_appt"]]
    assert completed.json() == []


async def test_list_excludes_other_users_appointments(client: AsyncClient, tenants: dict[str, Any]) -> None:
    response = await client.get("/api/appointments", headers=auth_headers(tenants["a"]))

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("query", [{"status": "paid"}, {"from": "yesterday"}])
async def test_list_rejects_invalid_query(client: AsyncClient, tenants: dict[str, Any], query: dict[str, str]) -> None:
    response = await client.get("/api/appointments", params=query, headers=auth_headers(tenants["b"]))

    assert response.status_code == 422


async def test_patch_marks_completed(client: AsyncClient, tenants: dict[str, Any]) -> None:
    response = await client.patch(
        f"/api/appointments/{tenants['b_appt']}",
        json={"status": "completed", "fee_inr": "320.00"},
        headers=auth_headers(tenants["b"]),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["fee_inr"] == "320.00"


async def test_patch_another_users_appointment_is_404(client: AsyncClient, tenants: dict[str, Any]) -> None:
    response = await client.patch(
        f"/api/appointments/{tenants['b_appt']}",
        json={"status": "no_show"},
        headers=auth_headers(tenants["a"]),
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [{"status": "paid"}, {"fee_inr": None}, {"starts_at": "2026-10-28T05:00:00"}, {"notes": "x" * 501}],
)
async def test_patch_rejects_invalid_input(client: AsyncClient, tenants: dict[str, Any], payload: dict[str, Any]) -> None:
    response = await client.patch(
        f"/api/appointments/{tenants['b_appt']}", json=payload, headers=auth_headers(tenants["b"])
    )

    assert response.status_code == 422


async def test_patch_invalid_uuid_is_422(client: AsyncClient, tenants: dict[str, Any]) -> None:
    response = await client.patch("/api/appointments/not-a-uuid", json={"status": "no_show"}, headers=auth_headers(tenants["b"]))

    assert response.status_code == 422

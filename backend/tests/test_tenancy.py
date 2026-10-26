"""SEC-09: references to another tenant's contact or deal are refused with 404."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.models.deal import Deal
from app.models.user import User
from tests.conftest import auth_headers


@pytest.fixture
async def tenants(db: AsyncSession, make_user: Callable[..., Awaitable[User]]) -> dict[str, Any]:
    """User A owns a contact and a deal; user B owns one deal of their own."""
    a, b = await make_user(), await make_user()
    a_contact = Contact(user_id=a.id, name="A's patient")
    a_deal = Deal(user_id=a.id, title="A's deal")
    b_deal = Deal(user_id=b.id, title="B's deal")
    db.add_all([a_contact, a_deal, b_deal])
    await db.commit()
    return {"b": b, "a_contact": str(a_contact.id), "a_deal": str(a_deal.id), "b_deal": str(b_deal.id)}


@pytest.mark.parametrize(
    ("method", "url", "payload"),
    [
        ("post", "/api/deals/", {"title": "x", "contact_id": "{a_contact}"}),
        ("patch", "/api/deals/{b_deal}", {"contact_id": "{a_contact}"}),
        ("post", "/api/activities/", {"description": "x", "occurred_at": "2026-10-26T10:00:00Z", "contact_id": "{a_contact}"}),
        ("post", "/api/activities/", {"description": "x", "occurred_at": "2026-10-26T10:00:00Z", "deal_id": "{a_deal}"}),
    ],
)
async def test_cross_tenant_fk_reference_rejected(
    client: AsyncClient, tenants: dict[str, Any], method: str, url: str, payload: dict[str, Any]
) -> None:
    body = {k: v.format(**tenants) if isinstance(v, str) else v for k, v in payload.items()}

    response = await client.request(method.upper(), url.format(**tenants), json=body, headers=auth_headers(tenants["b"]))

    assert response.status_code == 404


async def test_own_fk_reference_allowed(client: AsyncClient, db: AsyncSession, tenants: dict[str, Any]) -> None:
    own = Contact(user_id=tenants["b"].id, name="B's patient")
    db.add(own)
    await db.commit()

    response = await client.post(
        "/api/deals/", json={"title": "x", "contact_id": str(own.id)}, headers=auth_headers(tenants["b"])
    )

    assert response.status_code == 201

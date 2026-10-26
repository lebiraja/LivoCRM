"""SEC-14: bad payloads are 422s (never 500s); DB conflicts map to 409/422; SEC-22 bad tokens are 401s."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from fastapi import Request
from httpx import AsyncClient
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import data_error_handler, integrity_error_handler
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.user import User
from app.services.auth_service import create_access_token
from tests.conftest import auth_headers


@pytest.fixture
async def owner(make_user: Callable[..., Awaitable[User]]) -> User:
    return await make_user()


@pytest.fixture
async def deal_id(db: AsyncSession, owner: User) -> str:
    deal = Deal(user_id=owner.id, title="AMC", value=10)
    db.add(deal)
    await db.commit()
    return str(deal.id)


@pytest.fixture
async def contact_id(db: AsyncSession, owner: User) -> str:
    contact = Contact(user_id=owner.id, name="Asha")
    db.add(contact)
    await db.commit()
    return str(contact.id)


ACTIVITY = {"description": "Called", "occurred_at": "2026-10-26T10:00:00Z"}

INVALID_CREATES: list[tuple[str, dict[str, Any]]] = [
    ("/api/contacts/", {"name": ""}),
    ("/api/contacts/", {"name": "x" * 256}),
    ("/api/contacts/", {"name": "A", "email": "not-an-email"}),
    ("/api/contacts/", {"name": "A", "phone": "9" * 51}),
    ("/api/contacts/", {"name": "A", "tags": ["t"] * 21}),
    ("/api/contacts/", {"name": "A", "notes": "n" * 5001}),
    ("/api/deals/", {"title": "D", "value": -1}),
    ("/api/deals/", {"title": "D", "value": "1.005"}),
    ("/api/deals/", {"title": "D", "stage": "won"}),
    ("/api/deals/", {"title": "D", "status": "open"}),
    ("/api/deals/", {"title": "x" * 256}),
    ("/api/activities/", {**ACTIVITY, "type": "sms"}),
    ("/api/activities/", {**ACTIVITY, "description": ""}),
    ("/api/pipeline-stages/", {"name": "x" * 101}),
    ("/api/pipeline-stages/", {"name": "Lead2", "position": 3_000_000_000}),
]


@pytest.mark.parametrize(("url", "payload"), INVALID_CREATES)
async def test_invalid_payloads_return_422(client: AsyncClient, owner: User, url: str, payload: dict[str, Any]) -> None:
    response = await client.post(url, json=payload, headers=auth_headers(owner))

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload", [{"stage": "won"}, {"status": "open"}, {"value": -5}, {"title": None}, {"value": None}]
)
async def test_invalid_deal_update_returns_422(
    client: AsyncClient, owner: User, deal_id: str, payload: dict[str, Any]
) -> None:
    response = await client.patch(f"/api/deals/{deal_id}", json=payload, headers=auth_headers(owner))

    assert response.status_code == 422


async def test_invalid_stage_move_returns_422(client: AsyncClient, owner: User, deal_id: str) -> None:
    response = await client.patch(f"/api/deals/{deal_id}/stage", json={"stage": "done"}, headers=auth_headers(owner))

    assert response.status_code == 422


@pytest.mark.parametrize("payload", [{"name": None}, {"email": "bad"}, {"tags": None}])
async def test_invalid_contact_update_returns_422(
    client: AsyncClient, owner: User, contact_id: str, payload: dict[str, Any]
) -> None:
    response = await client.patch(f"/api/contacts/{contact_id}", json=payload, headers=auth_headers(owner))

    assert response.status_code == 422


async def test_contact_update_allows_clearing_email(
    client: AsyncClient, owner: User, contact_id: str
) -> None:
    response = await client.patch(f"/api/contacts/{contact_id}", json={"email": ""}, headers=auth_headers(owner))

    assert response.status_code == 200


async def test_duplicate_stage_name_is_409(client: AsyncClient, owner: User) -> None:
    headers = auth_headers(owner)
    assert (await client.post("/api/pipeline-stages/", json={"name": "Won"}, headers=headers)).status_code == 201

    response = await client.post("/api/pipeline-stages/", json={"name": "Won"}, headers=headers)

    assert response.status_code == 409


async def test_db_error_handlers() -> None:
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    orig = Exception("detail with user data")

    conflict = await integrity_error_handler(request, IntegrityError("stmt", {}, orig))
    invalid = await data_error_handler(request, DataError("stmt", {}, orig))

    assert conflict.status_code == 409 and b"user data" not in conflict.body
    assert invalid.status_code == 422 and b"user data" not in invalid.body


@pytest.mark.parametrize(
    "claims", [{"sub": "not-a-uuid"}, {"sub": ""}, {"other": "x"}, {"sub": "00000000-0000-0000-0000-000000000000"}]
)
async def test_bad_sub_is_401(client: AsyncClient, claims: dict[str, str]) -> None:
    headers = {"Authorization": f"Bearer {create_access_token(claims)}"}

    response = await client.get("/api/auth/me", headers=headers)

    assert response.status_code == 401

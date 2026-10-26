"""SEC-05/06/08/15, CA-05/07/10: chat saves validate model output, fail softly, and publish after commit."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.models.activity import Activity
from app.models.chat import ChatAction, ChatMessage
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.user import User
from app.routers import chat
from app.schemas.ai_actions import ContactFields
from app.services import session_manager
from app.services.ai_engine.data_extractor import extract_data
from app.services.ai_engine.intent_classifier import Intent
from app.services.ai_engine.orchestrator import SessionContext, SessionState
from tests.conftest import auth_headers
from tests.fakes import FakeLLMProvider


async def _confirming(client: AsyncClient, user: User, intent: Intent, data: dict[str, Any]) -> str:
    """Open a chat session whose context is waiting for a yes/no on `data`."""
    session_id = (await client.post("/api/chat/sessions", headers=auth_headers(user))).json()["id"]
    ctx = SessionContext(state=SessionState.CONFIRMING, intent=intent, collected_data=data)
    await session_manager._save_context(user.id, UUID(session_id), ctx)
    return session_id


async def _say(client: AsyncClient, user: User, session_id: str, text: str) -> Any:
    return await client.post(
        f"/api/chat/sessions/{session_id}/message", json={"message": text}, headers=auth_headers(user)
    )


async def _count(db: AsyncSession, model: type, **where: Any) -> int:
    stmt = select(func.count()).select_from(model)
    for column, value in where.items():
        stmt = stmt.where(getattr(model, column) == value)
    return int(await db.scalar(stmt) or 0)


@pytest.fixture
async def user(make_user: Callable[..., Awaitable[User]]) -> User:
    return await make_user()


async def test_no_dont_save_saves_nothing(client: AsyncClient, db: AsyncSession, user: User) -> None:
    sid = await _confirming(client, user, Intent.ADD_CONTACT, {"name": "Priya"})

    response = await _say(client, user, sid, "no, don't save")

    assert response.status_code == 200
    assert response.json()["session_state"] == "COLLECTING"
    assert await _count(db, Contact, user_id=user.id) == 0


async def test_contact_provenance_and_tags(client: AsyncClient, db: AsyncSession, user: User) -> None:
    sid = await _confirming(client, user, Intent.ADD_CONTACT, {"name": "Priya", "tags": ["vip"], "email": "P@x.io"})

    response = await _say(client, user, sid, "yes")

    assert response.status_code == 200
    contact = (await db.scalars(select(Contact).where(Contact.user_id == user.id))).one()
    assert (contact.tags, contact.source, contact.ai_session_id) == (["vip"], "ai_chat", UUID(sid))
    action = (await db.scalars(select(ChatAction).where(ChatAction.session_id == UUID(sid)))).one()
    assert (action.status, action.entity_type, action.entity_id) == ("completed", "contact", contact.id)


async def test_deal_fields_persisted(client: AsyncClient, db: AsyncSession, user: User) -> None:
    db.add(Contact(user_id=user.id, name="Priya"))
    await db.commit()
    data = {"title": "Clinic AMC", "value": "45000.50", "stage": "proposal", "contact_name": "priya",
            "expected_close": "2026-12-01"}
    sid = await _confirming(client, user, Intent.ADD_DEAL, data)

    await _say(client, user, sid, "yes")

    deal = (await db.scalars(select(Deal).where(Deal.user_id == user.id))).one()
    assert (deal.value, deal.stage, deal.expected_close) == (Decimal("45000.50"), "proposal", date(2026, 12, 1))
    assert deal.contact_id is not None and deal.source == "ai_chat"


async def test_activity_type_mapped(client: AsyncClient, db: AsyncSession, user: User) -> None:
    sid = await _confirming(client, user, Intent.LOG_ACTIVITY, {"activity_type": "call", "description": "Called"})

    await _say(client, user, sid, "yes")

    activity = (await db.scalars(select(Activity).where(Activity.user_id == user.id))).one()
    assert activity.type == "call"


@pytest.mark.parametrize(
    ("data", "field"),
    [
        ({"title": "AMC", "stage": "won"}, "stage"),
        ({"title": "AMC", "value": "5k"}, "value"),
        ({"title": "AMC", "value": -10}, "value"),
        ({"title": "AMC", "admin": True}, "admin"),
    ],
)
async def test_bad_deal_gives_clarification(
    client: AsyncClient, db: AsyncSession, user: User, data: dict[str, Any], field: str
) -> None:
    sid = await _confirming(client, user, Intent.ADD_DEAL, data)

    response = await _say(client, user, sid, "yes")

    assert response.status_code == 200
    body = response.json()
    assert field in body["ai_message"]["content"]
    assert body["session_state"] == "COLLECTING"
    assert await _count(db, Deal, user_id=user.id) == 0
    assert await _count(db, ChatMessage, session_id=UUID(sid)) == 2
    action = (await db.scalars(select(ChatAction).where(ChatAction.session_id == UUID(sid)))).one()
    assert (action.status, action.entity_type) == ("failed", "deal")


async def test_update_not_found_asks_instead_of_creating(client: AsyncClient, db: AsyncSession, user: User) -> None:
    sid = await _confirming(client, user, Intent.UPDATE_CONTACT, {"name": "Nobody", "phone": "123"})

    response = await _say(client, user, sid, "yes")

    assert "Nobody" in response.json()["ai_message"]["content"]
    assert await _count(db, Contact, user_id=user.id) == 0


async def test_update_uses_exact_name(client: AsyncClient, db: AsyncSession, user: User) -> None:
    db.add_all([Contact(user_id=user.id, name="John"), Contact(user_id=user.id, name="Johnson")])
    await db.commit()
    sid = await _confirming(client, user, Intent.UPDATE_CONTACT, {"name": "john", "phone": "555"})

    await _say(client, user, sid, "yes")

    phones = dict((await db.execute(select(Contact.name, Contact.phone).where(Contact.user_id == user.id))).all())
    assert phones == {"John": "555", "Johnson": ""}


async def test_update_ambiguous_name_lists_candidates(client: AsyncClient, db: AsyncSession, user: User) -> None:
    db.add_all([Contact(user_id=user.id, name="Ravi", company="A"), Contact(user_id=user.id, name="Ravi", company="B")])
    await db.commit()
    sid = await _confirming(client, user, Intent.UPDATE_CONTACT, {"name": "Ravi", "phone": "1"})

    response = await _say(client, user, sid, "yes")

    assert "2" in response.json()["ai_message"]["content"]
    assert await _count(db, Contact, user_id=user.id, phone="1") == 0


async def test_extract_schema_forbids_unknown_keys(llm: FakeLLMProvider) -> None:
    llm.script('{"extracted": {"name": "Asha", "_entity_id": "x", "is_admin": true}, "missing_required": []}')

    result = extract_data("ADD_CONTACT", "Add Asha", already_collected={"_entity_id": "server-side"})

    assert result.extracted == {"name": "Asha", "_entity_id": "server-side"}
    with pytest.raises(ValidationError):
        ContactFields.model_validate({"name": "Asha", "is_admin": True})


@pytest.mark.slow
async def test_concurrent_confirm_single_entity(
    live_client: AsyncClient, live_engine: AsyncEngine, live_user: User, llm: FakeLLMProvider
) -> None:
    sid = await _confirming(live_client, live_user, Intent.ADD_CONTACT, {"name": "Meena"})
    llm.delay = 0.3  # long confirmations trigger a classify call, widening the race window

    first, second = await asyncio.gather(
        _say(live_client, live_user, sid, "yes please go ahead now"),
        _say(live_client, live_user, sid, "yes please go ahead now"),
    )

    assert sorted([first.status_code, second.status_code]) == [200, 409]
    async with AsyncSession(live_engine) as db:
        assert await _count(db, Contact, user_id=live_user.id) == 1


@pytest.mark.slow
async def test_event_published_after_commit(
    live_client: AsyncClient, live_engine: AsyncEngine, live_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    visible: list[bool] = []

    async def _record(user_id: Any, entity_type: str, entity_id: Any, data: Any = None) -> None:
        async with AsyncSession(live_engine) as other:
            visible.append(await other.get(Contact, UUID(str(entity_id))) is not None)

    monkeypatch.setattr(chat, "push_entity_created", _record)
    sid = await _confirming(live_client, live_user, Intent.ADD_CONTACT, {"name": "Kavya"})

    await _say(live_client, live_user, sid, "yes")

    assert visible == [True]

"""Follow-up tasks API: list, draft, approve (one outbound message), skip. Other users' rows answer 404."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment
from app.models.contact import Contact
from app.models.follow_up import FollowUpTask
from app.models.outbound_message import OutboundMessage
from app.models.user import User
from app.services import draft_service
from tests.conftest import auth_headers
from tests.fakes import FakeLLMProvider

START = datetime(2026, 10, 27, 4, 30, tzinfo=UTC)  # 10:00 IST


@pytest.fixture
async def tenants(db: AsyncSession, make_user: Callable[..., Awaitable[User]]) -> dict[str, Any]:
    """User A owns a patient with a pending reminder; user B owns a pending reminder of their own."""
    a, b = await make_user(), await make_user()
    a_contact = Contact(user_id=a.id, name="Murugan", phone="+919000000001")
    b_contact = Contact(user_id=b.id, name="Lakshmi", phone="+919000000002")
    db.add_all([a_contact, b_contact])
    await db.commit()
    a_appt = Appointment(user_id=a.id, contact_id=a_contact.id, starts_at=START, fee_inr=Decimal("300"))
    b_appt = Appointment(user_id=b.id, contact_id=b_contact.id, starts_at=START, fee_inr=Decimal("300"))
    db.add_all([a_appt, b_appt])
    await db.commit()
    a_task = FollowUpTask(
        user_id=a.id, contact_id=a_contact.id, appointment_id=a_appt.id,
        reason="reminder_24h", due_at=START - timedelta(hours=24),
    )
    b_task = FollowUpTask(
        user_id=b.id, contact_id=b_contact.id, appointment_id=b_appt.id,
        reason="reminder_24h", due_at=START - timedelta(hours=24),
    )
    db.add_all([a_task, b_task])
    await db.commit()
    return {
        "a": a,
        "b": b,
        "a_contact": a_contact.id,
        "a_task": str(a_task.id),
        "b_task": str(b_task.id),
        "a_task_row": a_task,
    }


async def test_list_pending_returns_contact_details(client: AsyncClient, tenants: dict[str, Any]) -> None:
    response = await client.get("/api/follow-ups", params={"status": "pending"}, headers=auth_headers(tenants["a"]))

    assert response.status_code == 200
    rows = response.json()
    assert [row["id"] for row in rows] == [tenants["a_task"]]
    assert rows[0]["contact_name"] == "Murugan"
    assert rows[0]["contact_phone"] == "+919000000001"
    assert rows[0]["channel"] == "simulated"


async def test_list_due_before_filters(client: AsyncClient, tenants: dict[str, Any]) -> None:
    headers = auth_headers(tenants["a"])

    early = await client.get("/api/follow-ups", params={"due_before": "2026-10-25T00:00:00Z"}, headers=headers)
    late = await client.get("/api/follow-ups", params={"due_before": "2026-10-28T00:00:00Z"}, headers=headers)

    assert early.json() == []
    assert len(late.json()) == 1


@pytest.mark.parametrize("query", [{"status": "archived"}, {"due_before": "soon"}])
async def test_list_rejects_invalid_query(client: AsyncClient, tenants: dict[str, Any], query: dict[str, str]) -> None:
    response = await client.get("/api/follow-ups", params=query, headers=auth_headers(tenants["a"]))

    assert response.status_code == 422


async def test_draft_falls_back_to_template_when_llm_fails(client: AsyncClient, tenants: dict[str, Any]) -> None:
    # The autouse fake LLM has no scripted reply, so the call raises like a failed Bedrock/Groq call
    response = await client.post(f"/api/follow-ups/{tenants['a_task']}/draft", json={}, headers=auth_headers(tenants["a"]))

    assert response.status_code == 200
    body = response.json()
    assert "Murugan" in body["draft_en"]
    assert "10:00 AM" in body["draft_en"]
    assert "Murugan" in body["draft_ta"]
    assert "10:00 AM" in body["draft_ta"]
    assert body["status"] == "pending"


async def test_draft_uses_llm_reply_when_valid(client: AsyncClient, tenants: dict[str, Any], llm: FakeLLMProvider) -> None:
    llm.script('{"en": "Your visit is tomorrow at 10:00 AM IST.", "ta": "நாளை காலை 10:00 மணிக்கு சந்திப்பு."}')

    response = await client.post(f"/api/follow-ups/{tenants['a_task']}/draft", json={}, headers=auth_headers(tenants["a"]))

    assert response.json()["draft_en"] == "Your visit is tomorrow at 10:00 AM IST."
    assert response.json()["draft_ta"] == "நாளை காலை 10:00 மணிக்கு சந்திப்பு."


async def test_draft_prompt_carries_no_patient_identifiers(
    client: AsyncClient, tenants: dict[str, Any], llm: FakeLLMProvider
) -> None:
    llm.script('{"en": "Reminder: 10:00 AM IST.", "ta": "நினைவூட்டல்."}')

    await client.post(f"/api/follow-ups/{tenants['a_task']}/draft", json={}, headers=auth_headers(tenants["a"]))

    sent = str(llm.calls[0]["messages"]) + llm.calls[0]["system"][0]["text"]
    assert "Murugan" not in sent
    assert "+919000000001" not in sent


async def test_draft_falls_back_when_llm_output_is_malformed(
    client: AsyncClient, tenants: dict[str, Any], llm: FakeLLMProvider
) -> None:
    llm.script("Sure! Here is your draft: no json at all")

    response = await client.post(f"/api/follow-ups/{tenants['a_task']}/draft", json={}, headers=auth_headers(tenants["a"]))

    assert response.status_code == 200
    assert "Murugan" in response.json()["draft_en"]


async def test_draft_falls_back_when_llm_raises(
    client: AsyncClient, tenants: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(**_: Any) -> str:
        raise RuntimeError("provider exploded")

    monkeypatch.setattr(draft_service, "chat_completion", _boom)

    response = await client.post(f"/api/follow-ups/{tenants['a_task']}/draft", json={}, headers=auth_headers(tenants["a"]))

    assert response.status_code == 200
    assert response.json()["draft_ta"]


async def test_draft_for_missed_visit_uses_recovery_wording(
    client: AsyncClient, db: AsyncSession, tenants: dict[str, Any]
) -> None:
    missed = Appointment(
        user_id=tenants["a"].id, contact_id=tenants["a_contact"], starts_at=START, fee_inr=Decimal("300"), status="no_show"
    )
    db.add(missed)
    await db.commit()
    task = FollowUpTask(
        user_id=tenants["a"].id, contact_id=tenants["a_contact"], appointment_id=missed.id,
        reason="no_show_recovery", due_at=START,
    )
    db.add(task)
    await db.commit()

    response = await client.post(f"/api/follow-ups/{task.id}/draft", json={}, headers=auth_headers(tenants["a"]))

    assert "we missed you" in response.json()["draft_en"]


async def test_draft_for_manual_task_mentions_no_time(
    client: AsyncClient, db: AsyncSession, tenants: dict[str, Any]
) -> None:
    task = FollowUpTask(user_id=tenants["a"].id, contact_id=tenants["a_contact"], reason="manual", due_at=START)
    db.add(task)
    await db.commit()

    response = await client.post(f"/api/follow-ups/{task.id}/draft", json={}, headers=auth_headers(tenants["a"]))

    assert "this is the clinic" in response.json()["draft_en"]
    assert "IST" not in response.json()["draft_en"]


async def test_draft_after_approval_is_409(client: AsyncClient, tenants: dict[str, Any]) -> None:
    headers = auth_headers(tenants["a"])
    await client.post(f"/api/follow-ups/{tenants['a_task']}/approve", json={"language": "en", "body": "Hi"}, headers=headers)

    response = await client.post(f"/api/follow-ups/{tenants['a_task']}/draft", json={}, headers=headers)

    assert response.status_code == 409


async def test_draft_another_users_task_is_404(client: AsyncClient, tenants: dict[str, Any]) -> None:
    response = await client.post(f"/api/follow-ups/{tenants['b_task']}/draft", json={}, headers=auth_headers(tenants["a"]))

    assert response.status_code == 404


async def test_draft_invalid_id_is_422(client: AsyncClient, tenants: dict[str, Any]) -> None:
    response = await client.post("/api/follow-ups/not-a-uuid/draft", json={}, headers=auth_headers(tenants["a"]))

    assert response.status_code == 422


async def test_approve_creates_exactly_one_outbound_message(
    client: AsyncClient, db: AsyncSession, tenants: dict[str, Any]
) -> None:
    task = tenants["a_task_row"]
    task.draft_en = "Reminder: 10:00 AM IST."
    task.draft_ta = "நினைவூட்டல்."
    await db.commit()

    response = await client.post(
        f"/api/follow-ups/{tenants['a_task']}/approve", json={"language": "en"}, headers=auth_headers(tenants["a"])
    )

    assert response.status_code == 200
    body = response.json()
    assert body["task"]["status"] == "done"
    assert body["message"]["body"] == "Reminder: 10:00 AM IST."
    assert body["message"]["channel"] == "simulated"
    assert body["message"]["status"] == "sent"
    assert body["message"]["language"] == "en"
    count = await db.scalar(select(func.count()).select_from(OutboundMessage).where(OutboundMessage.task_id == task.id))
    assert count == 1


async def test_approve_with_edited_body_uses_body(client: AsyncClient, db: AsyncSession, tenants: dict[str, Any]) -> None:
    response = await client.post(
        f"/api/follow-ups/{tenants['a_task']}/approve",
        json={"language": "ta", "body": "நான் திருத்திய செய்தி."},
        headers=auth_headers(tenants["a"]),
    )

    assert response.status_code == 200
    assert response.json()["message"]["body"] == "நான் திருத்திய செய்தி."
    assert response.json()["message"]["language"] == "ta"


async def test_approve_twice_creates_no_second_message(
    client: AsyncClient, db: AsyncSession, tenants: dict[str, Any]
) -> None:
    headers = auth_headers(tenants["a"])
    await client.post(f"/api/follow-ups/{tenants['a_task']}/approve", json={"language": "en", "body": "Hi"}, headers=headers)

    second = await client.post(
        f"/api/follow-ups/{tenants['a_task']}/approve", json={"language": "en", "body": "Hi again"}, headers=headers
    )

    assert second.status_code == 409
    count = await db.scalar(
        select(func.count()).select_from(OutboundMessage).where(OutboundMessage.task_id == tenants["a_task_row"].id)
    )
    assert count == 1


async def test_approve_without_draft_or_body_is_409(client: AsyncClient, tenants: dict[str, Any]) -> None:
    response = await client.post(
        f"/api/follow-ups/{tenants['a_task']}/approve", json={"language": "en"}, headers=auth_headers(tenants["a"])
    )

    assert response.status_code == 409


async def test_approve_another_users_task_is_404(client: AsyncClient, tenants: dict[str, Any]) -> None:
    response = await client.post(
        f"/api/follow-ups/{tenants['b_task']}/approve",
        json={"language": "en", "body": "Hi"},
        headers=auth_headers(tenants["a"]),
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [{"language": "fr", "body": "Hi"}, {"body": "Hi"}, {"language": "en", "body": ""}, {"language": "en", "body": "x" * 1001}],
)
async def test_approve_rejects_invalid_input(client: AsyncClient, tenants: dict[str, Any], payload: dict[str, str]) -> None:
    response = await client.post(
        f"/api/follow-ups/{tenants['a_task']}/approve", json=payload, headers=auth_headers(tenants["a"])
    )

    assert response.status_code == 422


async def test_skip_marks_skipped(client: AsyncClient, tenants: dict[str, Any]) -> None:
    response = await client.post(f"/api/follow-ups/{tenants['a_task']}/skip", json={}, headers=auth_headers(tenants["a"]))

    assert response.status_code == 200
    assert response.json()["status"] == "skipped"


async def test_skip_after_approve_is_409(client: AsyncClient, tenants: dict[str, Any]) -> None:
    headers = auth_headers(tenants["a"])
    await client.post(f"/api/follow-ups/{tenants['a_task']}/approve", json={"language": "en", "body": "Hi"}, headers=headers)

    response = await client.post(f"/api/follow-ups/{tenants['a_task']}/skip", json={}, headers=headers)

    assert response.status_code == 409


async def test_skip_another_users_task_is_404(client: AsyncClient, tenants: dict[str, Any]) -> None:
    response = await client.post(f"/api/follow-ups/{tenants['b_task']}/skip", json={}, headers=auth_headers(tenants["a"]))

    assert response.status_code == 404


async def test_skip_invalid_id_is_422(client: AsyncClient, tenants: dict[str, Any]) -> None:
    response = await client.post("/api/follow-ups/nope/skip", json={}, headers=auth_headers(tenants["a"]))

    assert response.status_code == 422

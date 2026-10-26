"""CA-12 lead-score recency input; CA-27 extractor prompt braces."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.contact import Contact
from app.models.user import User
from app.routers import ai
from app.services.ai_engine.prompts import DATA_EXTRACTOR_SYSTEM
from tests.conftest import auth_headers


async def test_lead_score_uses_days_since_last_activity(
    client: AsyncClient, db: AsyncSession, make_user: Callable[..., Awaitable[User]], monkeypatch: pytest.MonkeyPatch
) -> None:
    user = await make_user()
    contact = Contact(user_id=user.id, name="Asha")
    db.add(contact)
    await db.flush()
    now = datetime.now(timezone.utc)
    db.add_all([
        Activity(user_id=user.id, contact_id=contact.id, description="old", occurred_at=now - timedelta(days=40)),
        Activity(user_id=user.id, contact_id=contact.id, description="recent", occurred_at=now - timedelta(days=10)),
    ])
    await db.commit()
    seen: list[dict[str, Any]] = []
    monkeypatch.setattr(ai, "score_contact", lambda data: seen.append(data) or {"score": 1, "label": "warm"})

    response = await client.get(f"/api/ai/score/{contact.id}", headers=auth_headers(user))

    assert response.status_code == 200
    assert (seen[0]["activity_count"], seen[0]["days_since_last_activity"]) == (2, 10)


def test_extractor_prompt_has_single_braces() -> None:
    assert "{{" not in DATA_EXTRACTOR_SYSTEM and '{"extracted": {' in DATA_EXTRACTOR_SYSTEM

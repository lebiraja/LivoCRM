"""SEC-20 / CA-13: chat context lives only in Redis, bound to its owner, with a TTL."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fakeredis import FakeAsyncRedis

from app.services import session_manager
from app.services.ai_engine.intent_classifier import Intent
from app.services.ai_engine.orchestrator import SessionContext, SessionState


async def test_context_survives_process_restart(fake_redis: FakeAsyncRedis) -> None:
    user_id, session_id = uuid4(), uuid4()
    ctx = SessionContext(state=SessionState.COLLECTING, intent=Intent.ADD_CONTACT, collected_data={"name": "Asha"})

    await session_manager._save_context(user_id, session_id, ctx)

    assert not hasattr(session_manager, "_context_store")
    restored = await session_manager.get_context(user_id, session_id)
    assert (restored.state, restored.intent, restored.collected_data) == (ctx.state, ctx.intent, ctx.collected_data)
    key = f"livocrm:ctx:{user_id}:{session_id}"
    assert 0 < await fake_redis.ttl(key) <= 3600


async def test_context_bound_to_user() -> None:
    owner, session_id = uuid4(), uuid4()
    await session_manager._save_context(owner, session_id, SessionContext(state=SessionState.CONFIRMING))

    assert (await session_manager.get_context(uuid4(), session_id)).state == SessionState.IDLE


async def test_redis_down_gives_fresh_context(fake_redis: FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch) -> None:
    from redis.exceptions import ConnectionError as RedisConnectionError

    async def _down(*args: object, **kwargs: object) -> None:
        raise RedisConnectionError("down")

    monkeypatch.setattr(fake_redis, "get", _down)

    assert (await session_manager.get_context(uuid4(), uuid4())).state == SessionState.IDLE

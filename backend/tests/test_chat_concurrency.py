"""SEC-02 / SEC-07: slow LLM calls must neither block the event loop nor hold DB connections."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.models.user import User
from app.services import bedrock_service
from tests.conftest import TEST_DATABASE_URL, auth_headers
from tests.fakes import FakeLLMProvider


async def _open_sessions(client: AsyncClient, user: User, n: int) -> list[str]:
    return [
        (await client.post("/api/chat/sessions", headers=auth_headers(user))).json()["id"]
        for _ in range(n)
    ]


def _send(client: AsyncClient, user: User, session_id: str) -> asyncio.Task[Any]:
    return asyncio.create_task(
        client.post(
            f"/api/chat/sessions/{session_id}/message",
            json={"message": "hello there"},
            headers=auth_headers(user),
        )
    )


@pytest.mark.slow
async def test_chat_does_not_block_loop(live_client: AsyncClient, live_user: User, llm: FakeLLMProvider) -> None:
    sessions = await _open_sessions(live_client, live_user, 5)
    llm.delay = 1.0
    chats = [_send(live_client, live_user, sid) for sid in sessions]
    await asyncio.sleep(0.2)

    worst = 0.0
    for _ in range(5):
        start = time.perf_counter()
        response = await live_client.get("/api/health")
        worst = max(worst, time.perf_counter() - start)
        assert response.status_code == 200

    results = await asyncio.gather(*chats)
    assert [r.status_code for r in results] == [200] * 5
    assert worst < 0.1


@pytest.fixture
async def live_engine() -> AsyncIterator[AsyncEngine]:
    """Two pooled connections only: any request that holds one across the LLM starves the rest."""
    engine = create_async_engine(TEST_DATABASE_URL, pool_size=2, max_overflow=0, pool_timeout=1)
    yield engine
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE users CASCADE"))
    await engine.dispose()


@pytest.mark.slow
async def test_pool_not_held_during_llm(live_client: AsyncClient, live_user: User, llm: FakeLLMProvider) -> None:
    sessions = await _open_sessions(live_client, live_user, 6)
    llm.delay = 0.6

    results = await asyncio.gather(*(_send(live_client, live_user, sid) for sid in sessions))

    assert [r.status_code for r in results] == [200] * 6


def test_bedrock_client_has_timeouts(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(bedrock_service, "_bedrock_client", None)
    monkeypatch.setattr(bedrock_service.boto3, "client", lambda *args, **kwargs: captured.update(kwargs))

    bedrock_service._get_client()

    config = captured["config"]
    assert (config.connect_timeout, config.read_timeout) == (3, 15)
    assert config.retries == {"max_attempts": 2}

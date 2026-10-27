"""Registration and login hygiene (SEC-12) and auth rate limits (SEC-03)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from fakeredis import FakeAsyncRedis
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pipeline import PipelineStage
from app.models.user import User
from app.routers import auth
from tests.conftest import auth_headers

PASSWORD = "correct-horse-battery"


async def _register(client: AsyncClient, email: str, password: str = PASSWORD) -> Any:
    return await client.post("/api/auth/register", json={"email": email, "password": password, "full_name": "A"})


async def test_register_ok(client: AsyncClient, db: AsyncSession) -> None:
    response = await _register(client, "Alice@Example.COM")

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert "hashed_password" not in body
    stages = await db.scalar(select(func.count()).select_from(PipelineStage).where(PipelineStage.user_id == body["id"]))
    assert stages == 6


async def test_register_case_insensitive_duplicate(client: AsyncClient) -> None:
    assert (await _register(client, "bob@example.com")).status_code == 201

    response = await _register(client, "BOB@Example.com")

    assert response.status_code == 409
    assert "already" not in response.json()["detail"].lower()


@pytest.mark.parametrize(
    ("password", "status"),
    [
        ("a" * 9, 422),
        ("a" * 10, 201),
        ("a" * 72, 201),
        ("a" * 73, 422),
        ("é" * 36, 201),  # 72 bytes
        ("é" * 37, 422),  # 74 bytes, 37 characters
    ],
)
async def test_register_password_policy(client: AsyncClient, password: str, status: int) -> None:
    assert (await _register(client, "pw@example.com", password)).status_code == status


async def test_lower_email_unique_index(db: AsyncSession) -> None:
    db.add_all([User(email="Case@x.io", hashed_password="h"), User(email="case@x.io", hashed_password="h")])

    with pytest.raises(IntegrityError):
        await db.flush()


async def test_login_ok_case_insensitive(client: AsyncClient) -> None:
    await _register(client, "carol@example.com")

    response = await client.post("/api/auth/login", json={"email": "Carol@Example.com", "password": PASSWORD})

    assert response.status_code == 200
    assert response.json() == {"authenticated": True}
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "livocrm_session=" in cookie


async def test_login_cookie_authenticates_and_logout_clears_it(client: AsyncClient) -> None:
    await _register(client, "cookie@example.com")
    login = await client.post("/api/auth/login", json={"email": "cookie@example.com", "password": PASSWORD})

    assert login.status_code == 200
    assert (await client.get("/api/auth/me")).status_code == 200
    logout = await client.post("/api/auth/logout")
    assert logout.status_code == 204
    assert "max-age=0" in logout.headers["set-cookie"].lower()
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_login_unknown_user_does_hash(
    client: AsyncClient, make_user: Callable[..., Awaitable[User]], monkeypatch: pytest.MonkeyPatch
) -> None:
    await make_user(email="dave@example.com", password=PASSWORD)
    calls: list[str] = []
    real_verify = auth.verify_password
    monkeypatch.setattr(auth, "verify_password", lambda raw, hashed: calls.append(hashed) or real_verify(raw, hashed))

    wrong = await client.post("/api/auth/login", json={"email": "dave@example.com", "password": "nope-nope-nope"})
    unknown = await client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "nope-nope-nope"})

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert len(calls) == 2


async def test_rate_limit_login(client: AsyncClient, fake_redis: FakeAsyncRedis) -> None:
    body = {"email": "erin@example.com", "password": "wrong-password"}
    statuses = [(await client.post("/api/auth/login", json=body)).status_code for _ in range(5)]
    blocked = await client.post("/api/auth/login", json=body)

    assert statuses == [401] * 5
    assert blocked.status_code == 429
    assert 0 < int(blocked.headers["Retry-After"]) <= 60
    keys = await fake_redis.keys("livocrm:rl:login:*")
    assert 0 < await fake_redis.ttl(keys[0]) <= 60


async def test_rate_limit_login_is_per_email(client: AsyncClient) -> None:
    for _ in range(5):
        await client.post("/api/auth/login", json={"email": "frank@example.com", "password": "wrong-password"})

    other = await client.post("/api/auth/login", json={"email": "gina@example.com", "password": "wrong-password"})

    assert other.status_code == 401


async def test_rate_limit_register(client: AsyncClient) -> None:
    statuses = [(await _register(client, f"r{i}@example.com")).status_code for i in range(4)]

    assert statuses == [201, 201, 201, 429]


async def test_rate_limit_chat_user_budget(client: AsyncClient, make_user: Callable[..., Awaitable[User]]) -> None:
    user = await make_user()
    headers = auth_headers(user)
    session_id = (await client.post("/api/chat/sessions", headers=headers)).json()["id"]
    url = f"/api/chat/sessions/{session_id}/message"

    statuses = [(await client.post(url, json={"message": "hi"}, headers=headers)).status_code for _ in range(31)]

    assert statuses == [200] * 30 + [429]


async def test_rate_limit_insights(client: AsyncClient, make_user: Callable[..., Awaitable[User]]) -> None:
    headers = auth_headers(await make_user())

    statuses = [(await client.post("/api/ai/insights", headers=headers)).status_code for _ in range(11)]

    assert statuses == [200] * 10 + [429]


async def test_rate_limit_fails_open(
    client: AsyncClient, fake_redis: FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from redis.exceptions import ConnectionError as RedisConnectionError

    def _down(*args: object, **kwargs: object) -> None:
        raise RedisConnectionError("redis down")

    monkeypatch.setattr(fake_redis, "pipeline", _down)

    response = await client.post("/api/auth/login", json={"email": "hal@example.com", "password": "wrong-password"})

    assert response.status_code == 401
    assert "rate limit" in caplog.text.lower()

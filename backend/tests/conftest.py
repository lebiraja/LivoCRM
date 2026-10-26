"""Shared fixtures: throwaway Postgres with per-test rollback, fake Redis, fake LLM, ASGI client."""

from __future__ import annotations

import asyncio
import os
import secrets
import subprocess
from collections.abc import AsyncIterator, Awaitable, Callable

# Settings are read at import time, so the test environment must exist first.
TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SECRET_KEY"] = secrets.token_urlsafe(48)
os.environ["BEDROCK_ENABLED"] = "true"

import pytest  # noqa: E402
from fakeredis import FakeAsyncRedis  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app import database  # noqa: E402
from app.dependencies import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import bedrock_service, session_manager  # noqa: E402
from app.services.auth_service import create_access_token, hash_password  # noqa: E402
from tests.fakes import FakeLLMProvider  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema() -> None:
    """Rebuild the test schema from migrations once per run."""

    async def _reset() -> None:
        engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
        async with engine.begin() as conn:
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
        await engine.dispose()

    asyncio.run(_reset())
    subprocess.run(["alembic", "upgrade", "head"], check=True, capture_output=True)


@pytest.fixture
async def db_conn() -> AsyncIterator[AsyncConnection]:
    """One connection per test inside an outer transaction that is always rolled back."""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.connect() as conn:
        trans = await conn.begin()
        yield conn
        await trans.rollback()
    await engine.dispose()


@pytest.fixture
async def db(db_conn: AsyncConnection) -> AsyncIterator[AsyncSession]:
    session = AsyncSession(bind=db_conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    yield session
    await session.close()


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeAsyncRedis:
    client = FakeAsyncRedis(decode_responses=True)
    monkeypatch.setattr(session_manager, "_redis", client)
    monkeypatch.setattr(session_manager, "_redis_available", True)
    monkeypatch.setattr(session_manager, "_context_store", {})
    return client


@pytest.fixture(autouse=True)
def llm(monkeypatch: pytest.MonkeyPatch) -> FakeLLMProvider:
    fake = FakeLLMProvider()
    monkeypatch.setattr(bedrock_service, "_get_client", lambda: fake)
    return fake


@pytest.fixture(autouse=True)
def _side_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Background work that opens its own session gets a fresh pool-less engine per test."""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(database, "async_session", factory)
    monkeypatch.setattr(database, "async_session_factory", factory)
    monkeypatch.setattr("app.services.analytics_cache.async_session_factory", factory)


@pytest.fixture
async def client(db_conn: AsyncConnection) -> AsyncIterator[AsyncClient]:
    async def _get_db() -> AsyncIterator[AsyncSession]:
        session = AsyncSession(bind=db_conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()

    app.dependency_overrides[get_db] = _get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(db: AsyncSession) -> Callable[..., Awaitable[User]]:
    async def _make(email: str | None = None, password: str = "correct-horse-battery") -> User:
        user = User(
            email=email or f"user-{secrets.token_hex(4)}@example.com",
            hashed_password=hash_password(password),
            full_name="Test User",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    return _make


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}

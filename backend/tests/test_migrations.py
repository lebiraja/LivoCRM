"""IA3 migrations (0008+) must downgrade and re-apply cleanly."""

import asyncio
import subprocess

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from tests.conftest import TEST_DATABASE_URL

CLINIC_TABLES = ("appointments", "follow_up_tasks", "outbound_messages")


def _alembic(*args: str) -> str:
    return subprocess.run(["alembic", *args], check=True, capture_output=True, text=True).stdout


async def _existing_tables() -> set[str]:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.connect() as conn:
        rows = await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        tables = {row[0] for row in rows}
    await engine.dispose()
    return tables


def test_new_revisions_round_trip() -> None:
    head = _alembic("current").split()[0]

    _alembic("downgrade", "0007")
    _alembic("upgrade", "head")

    assert _alembic("current").split()[0] == head


def test_clinic_tables_drop_and_restore() -> None:
    _alembic("downgrade", "0009")
    assert not set(CLINIC_TABLES) & asyncio.run(_existing_tables())

    _alembic("upgrade", "head")
    assert set(CLINIC_TABLES) <= asyncio.run(_existing_tables())

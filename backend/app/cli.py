"""Operator commands. Usage: `python -m app.cli seed-demo --email <owner email>`."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.database import async_session_factory
from app.models.user import User
from app.schemas.recovery import DemoSeedResponse
from app.services.demo_seed import seed_demo_data


async def seed_demo_for_email(email: str) -> DemoSeedResponse:
    async with async_session_factory() as db:
        owner = await db.scalar(select(User).where(func.lower(User.email) == email.lower()))
        if owner is None:
            raise SystemExit("No user has that email; register in the app first")
        return await seed_demo_data(db, owner.id, datetime.now(UTC))


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    seed = commands.add_parser("seed-demo", help="add idempotent clinic demo data to a user")
    seed.add_argument("--email", required=True, help="email of the account that owns the demo data")
    args = parser.parse_args()

    counts = asyncio.run(seed_demo_for_email(args.email))
    print(f"Demo data: {counts.contacts} new contacts, {counts.appointments} new appointments")


if __name__ == "__main__":
    main()

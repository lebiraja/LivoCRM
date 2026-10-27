"""Operator commands. Usage: `python -m app.cli seed-demo --email <owner email>`."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
from getpass import getpass

from sqlalchemy import func, select

from app.database import async_session_factory
from app.models.user import User
from app.schemas.user import UserCreate
from app.schemas.recovery import DemoSeedResponse
from app.services.demo_seed import seed_demo_data
from app.services.auth_service import hash_password
from app.services.seed_service import seed_default_pipeline_stages


async def seed_demo_for_email(email: str) -> DemoSeedResponse:
    async with async_session_factory() as db:
        owner = await db.scalar(select(User).where(func.lower(User.email) == email.lower()))
        if owner is None:
            raise SystemExit("No user has that email; register in the app first")
        return await seed_demo_data(db, owner.id, datetime.now(UTC))


async def create_user(email: str, full_name: str, password: str) -> None:
    body = UserCreate(email=email, full_name=full_name, password=password)
    async with async_session_factory() as db:
        existing = await db.scalar(select(User).where(func.lower(User.email) == body.email))
        if existing is not None:
            raise SystemExit("An account with that email already exists")
        user = User(email=body.email, hashed_password=hash_password(body.password), full_name=body.full_name)
        db.add(user)
        await db.flush()
        await seed_default_pipeline_stages(db, user.id)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    seed = commands.add_parser("seed-demo", help="add idempotent clinic demo data to a user")
    seed.add_argument("--email", required=True, help="email of the account that owns the demo data")
    create = commands.add_parser("create-user", help="create an account without public registration")
    create.add_argument("--email", required=True)
    create.add_argument("--full-name", required=True)
    args = parser.parse_args()

    if args.command == "seed-demo":
        counts = asyncio.run(seed_demo_for_email(args.email))
        print(f"Demo data: {counts.contacts} new contacts, {counts.appointments} new appointments")
    else:
        password = getpass("New account password (10-72 UTF-8 bytes): ")
        confirmation = getpass("Repeat password: ")
        if password != confirmation:
            raise SystemExit("Passwords did not match")
        asyncio.run(create_user(args.email, args.full_name, password))
        print(f"Created account for {args.email}")


if __name__ == "__main__":
    main()

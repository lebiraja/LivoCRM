"""One-time WebSocket tickets (SEC-10).

Browsers cannot set headers on a WebSocket handshake, so the JWT used to end
up in the URL (and in access logs). Instead the client exchanges its JWT for
an opaque ticket via `POST /api/ws/ticket` and connects with `?ticket=`. A
ticket lives 30 s in Redis, is bound to one user, one channel and (for chat)
one session, and is deleted the moment it is redeemed.
"""

from __future__ import annotations

import secrets
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.services.redis_client import get_redis

TICKET_TTL_SECONDS = 30
_PREFIX = "livocrm:wsticket:"


class TicketClaims(BaseModel):
    user_id: UUID
    channel: Literal["dashboard", "chat"]
    session_id: UUID | None = None


async def issue_ticket(claims: TicketClaims) -> str:
    ticket = secrets.token_urlsafe(32)
    await get_redis().set(f"{_PREFIX}{ticket}", claims.model_dump_json(), ex=TICKET_TTL_SECONDS)
    return ticket


async def redeem_ticket(ticket: str) -> TicketClaims | None:
    """Return the ticket's claims and delete it atomically, so it works once."""
    raw = await get_redis().getdel(f"{_PREFIX}{ticket}")
    return TicketClaims.model_validate_json(raw) if raw else None

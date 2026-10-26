"""WebSocket endpoints for real-time dashboard & chat updates.

Two WS endpoints:
  • /ws/dashboard/{user_id}  — pushes dashboard_update, entity_created
  • /ws/chat/{session_id}    — pushes ai_typing indicator

Both admit only a one-time ticket from POST /api/ws/ticket (SEC-10/19).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.chat import ChatSession
from app.models.user import User
from app.services.ws_tickets import TICKET_TTL_SECONDS, TicketClaims, issue_ticket, redeem_ticket

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])
# HTTP side (mounted under /api): exchange a JWT for a WebSocket ticket
ticket_router = APIRouter(prefix="/ws", tags=["websocket"])

_MAX_CONNECTIONS_PER_USER = 5


# ── Connection Manager ──────────────────────────────────────────────────────


class ConnectionManager:
    """In-memory registry of active WebSocket connections."""

    def __init__(self) -> None:
        # user_id → set of WebSocket connections
        self._dashboard: dict[str, set[WebSocket]] = defaultdict(set)
        # session_id → set of WebSocket connections
        self._chat: dict[str, set[WebSocket]] = defaultdict(set)
        # user_id → open sockets of either kind (capped per user)
        self._per_user: dict[str, int] = defaultdict(int)

    def connection_count(self, user_id: str) -> int:
        return self._per_user.get(user_id, 0)

    async def _admit(self, user_id: str, ws: WebSocket) -> bool:
        if self._per_user[user_id] >= _MAX_CONNECTIONS_PER_USER:
            await ws.close(code=4029, reason="Too many connections")
            logger.warning("WebSocket connection rejected: per-user cap reached")
            return False
        await ws.accept()
        self._per_user[user_id] += 1
        return True

    def _release(self, user_id: str) -> None:
        self._per_user[user_id] -= 1
        if self._per_user[user_id] <= 0:
            del self._per_user[user_id]

    # -- dashboard ---------------------------------------------------------

    async def connect_dashboard(self, user_id: str, ws: WebSocket) -> bool:
        if not await self._admit(user_id, ws):
            return False
        self._dashboard[user_id].add(ws)
        return True

    def disconnect_dashboard(self, user_id: str, ws: WebSocket) -> None:
        self._dashboard[user_id].discard(ws)
        if not self._dashboard[user_id]:
            del self._dashboard[user_id]
        self._release(user_id)

    async def broadcast_dashboard(self, user_id: str, event: dict) -> None:
        """Send an event to all dashboard connections for a user."""
        dead: list[WebSocket] = []
        for ws in self._dashboard.get(user_id, set()):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._dashboard[user_id].discard(ws)

    # -- chat --------------------------------------------------------------

    async def connect_chat(self, session_id: str, user_id: str, ws: WebSocket) -> bool:
        if not await self._admit(user_id, ws):
            return False
        self._chat[session_id].add(ws)
        return True

    def disconnect_chat(self, session_id: str, user_id: str, ws: WebSocket) -> None:
        self._chat[session_id].discard(ws)
        if not self._chat[session_id]:
            del self._chat[session_id]
        self._release(user_id)

    async def broadcast_chat(self, session_id: str, event: dict) -> None:
        """Send an event to all chat connections for a session."""
        dead: list[WebSocket] = []
        for ws in self._chat.get(session_id, set()):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._chat[session_id].discard(ws)


# Singleton — importable from other modules
manager = ConnectionManager()


# ── Helper: push from anywhere in the app ───────────────────────────────────


async def push_dashboard_update(user_id: str | UUID, data: dict | None = None) -> None:
    """Call from anywhere to push a dashboard refresh event."""
    await manager.broadcast_dashboard(
        str(user_id),
        {"type": "dashboard_update", "data": data or {}},
    )


async def push_entity_created(
    user_id: str | UUID,
    entity_type: str,
    entity_id: str | UUID,
    entity_data: dict | None = None,
) -> None:
    """Call from anywhere to push a new-entity notification."""
    await manager.broadcast_dashboard(
        str(user_id),
        {
            "type": "entity_created",
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "data": entity_data or {},
        },
    )


async def push_ai_typing(session_id: str | UUID, is_typing: bool = True) -> None:
    """Call from anywhere to push typing indicator."""
    await manager.broadcast_chat(
        str(session_id),
        {"type": "ai_typing", "is_typing": is_typing},
    )


# ── Ticket endpoint (HTTP) ──────────────────────────────────────────────────


class DashboardTicketRequest(BaseModel):
    channel: Literal["dashboard"]


class ChatTicketRequest(BaseModel):
    channel: Literal["chat"]
    session_id: UUID


class WsTicket(BaseModel):
    ticket: str
    expires_in: int


@ticket_router.post("/ticket", response_model=WsTicket)
async def create_ws_ticket(
    body: Annotated[DashboardTicketRequest | ChatTicketRequest, Field(discriminator="channel")],
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WsTicket:
    """Exchange the caller's JWT for a 30 s, single-use WebSocket ticket.

    Chat tickets are issued only for the caller's own session (SEC-19).
    """
    session_id = None
    if isinstance(body, ChatTicketRequest):
        session_id = await db.scalar(
            select(ChatSession.id).where(ChatSession.id == body.session_id, ChatSession.user_id == user.id)
        )
        if session_id is None:
            raise HTTPException(status_code=404, detail="Chat session not found")
    ticket = await issue_ticket(TicketClaims(user_id=user.id, channel=body.channel, session_id=session_id))
    return WsTicket(ticket=ticket, expires_in=TICKET_TTL_SECONDS)


# ── WebSocket Endpoints ────────────────────────────────────────────────────


async def _redeem(websocket: WebSocket, channel: Literal["dashboard", "chat"]) -> TicketClaims | None:
    """Admit only a fresh ticket for this channel; JWTs in the URL are never accepted."""
    ticket = websocket.query_params.get("ticket")
    if not ticket:
        await websocket.close(code=4001, reason="Missing ticket")
        logger.warning("WebSocket connection rejected (%s): missing ticket", channel)
        return None
    claims = await redeem_ticket(ticket)
    if claims is None:
        await websocket.close(code=4002, reason="Invalid or expired ticket")
        logger.warning("WebSocket connection rejected (%s): invalid ticket", channel)
        return None
    if claims.channel != channel:
        await websocket.close(code=4003, reason="Forbidden")
        logger.warning("WebSocket connection rejected (%s): ticket for another channel", channel)
        return None
    return claims


async def _serve(websocket: WebSocket, channel: str) -> None:
    """Answer pings until the client leaves; any error ends this socket only."""
    try:
        while True:
            # Keep connection alive — client may send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.warning("%s WebSocket closed after an error", channel, exc_info=True)


@router.websocket("/dashboard/{user_id}")
async def ws_dashboard(websocket: WebSocket, user_id: str):
    """Dashboard real-time updates.

    Clients simply connect and receive JSON events:
      {"type": "dashboard_update", "data": {...}}
      {"type": "entity_created", "entity_type": "contact", "entity_id": "...", "data": {...}}

    Requires a dashboard ticket in the query: ?ticket=<ticket>
    """
    claims = await _redeem(websocket, "dashboard")
    if claims is None:
        return
    if str(claims.user_id) != user_id:
        await websocket.close(code=4003, reason="Forbidden")
        logger.warning("WebSocket connection rejected (dashboard): user_id mismatch")
        return

    if not await manager.connect_dashboard(user_id, websocket):
        return
    try:
        await _serve(websocket, "dashboard")
    finally:
        manager.disconnect_dashboard(user_id, websocket)


@router.websocket("/chat/{session_id}")
async def ws_chat(websocket: WebSocket, session_id: str):
    """Chat typing indicator.

    Clients simply connect and receive JSON events:
      {"type": "ai_typing", "is_typing": true/false}

    Requires a chat ticket for this session in the query: ?ticket=<ticket>.
    Session ownership was checked when the ticket was issued.
    """
    claims = await _redeem(websocket, "chat")
    if claims is None:
        return
    if str(claims.session_id) != session_id:
        await websocket.close(code=4003, reason="Forbidden")
        logger.warning("WebSocket connection rejected (chat): session mismatch")
        return

    user_id = str(claims.user_id)
    if not await manager.connect_chat(session_id, user_id, websocket):
        return
    try:
        await _serve(websocket, "chat")
    finally:
        manager.disconnect_chat(session_id, user_id, websocket)

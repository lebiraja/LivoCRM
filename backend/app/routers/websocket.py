"""WebSocket endpoints for real-time dashboard & chat updates.

Two WS endpoints:
  • /ws/dashboard/{user_id}  — pushes dashboard_update, entity_created
  • /ws/chat/{session_id}    — pushes ai_typing indicator
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/ws", tags=["websocket"])


# ── Connection Manager ──────────────────────────────────────────────────────


class ConnectionManager:
    """In-memory registry of active WebSocket connections."""

    def __init__(self) -> None:
        # user_id → set of WebSocket connections
        self._dashboard: dict[str, set[WebSocket]] = defaultdict(set)
        # session_id → set of WebSocket connections
        self._chat: dict[str, set[WebSocket]] = defaultdict(set)

    # -- dashboard ---------------------------------------------------------

    async def connect_dashboard(self, user_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._dashboard[user_id].add(ws)

    def disconnect_dashboard(self, user_id: str, ws: WebSocket) -> None:
        self._dashboard[user_id].discard(ws)
        if not self._dashboard[user_id]:
            del self._dashboard[user_id]

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

    async def connect_chat(self, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._chat[session_id].add(ws)

    def disconnect_chat(self, session_id: str, ws: WebSocket) -> None:
        self._chat[session_id].discard(ws)
        if not self._chat[session_id]:
            del self._chat[session_id]

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


# ── WebSocket Endpoints ────────────────────────────────────────────────────


@router.websocket("/dashboard/{user_id}")
async def ws_dashboard(websocket: WebSocket, user_id: str):
    """Dashboard real-time updates.

    Clients simply connect and receive JSON events:
      {"type": "dashboard_update", "data": {...}}
      {"type": "entity_created", "entity_type": "contact", "entity_id": "...", "data": {...}}
    """
    await manager.connect_dashboard(user_id, websocket)
    try:
        while True:
            # Keep connection alive — client may send pings
            data = await websocket.receive_text()
            # Echo pings
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect_dashboard(user_id, websocket)


@router.websocket("/chat/{session_id}")
async def ws_chat(websocket: WebSocket, session_id: str):
    """Chat typing indicator.

    Clients simply connect and receive JSON events:
      {"type": "ai_typing", "is_typing": true/false}
    """
    await manager.connect_chat(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect_chat(session_id, websocket)

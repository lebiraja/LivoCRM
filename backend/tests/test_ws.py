"""SEC-10/19: WebSockets admit only one-time tickets bound to user, channel and chat session."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterator
from uuid import UUID, uuid4

import pytest
from fakeredis import FakeAsyncRedis
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.models.chat import ChatSession
from app.models.user import User
from app.routers.websocket import manager
from app.services.auth_service import create_access_token
from app.services.ws_tickets import TicketClaims, issue_ticket
from tests.conftest import auth_headers


# ── Ticket endpoint (httpx, shares the test transaction) ────────────────────

@pytest.fixture
async def user(make_user: Callable[..., Awaitable[User]]) -> User:
    return await make_user()


async def test_dashboard_ticket_contract(client: AsyncClient, user: User, fake_redis: FakeAsyncRedis) -> None:
    response = await client.post("/api/ws/ticket", json={"channel": "dashboard"}, headers=auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert body.keys() == {"ticket", "expires_in"} and body["expires_in"] == 30
    assert 0 < await fake_redis.ttl(f"livocrm:wsticket:{body['ticket']}") <= 30


async def test_chat_ticket_requires_owned_session(
    client: AsyncClient, db: AsyncSession, user: User, make_user: Callable[..., Awaitable[User]]
) -> None:
    other = await make_user()
    foreign = ChatSession(user_id=other.id)
    own = ChatSession(user_id=user.id)
    db.add_all([foreign, own])
    await db.commit()

    def ask(session_id: UUID) -> Awaitable[object]:
        body = {"channel": "chat", "session_id": str(session_id)}
        return client.post("/api/ws/ticket", json=body, headers=auth_headers(user))

    assert (await ask(own.id)).status_code == 200
    assert (await ask(foreign.id)).status_code == 404


@pytest.mark.parametrize("body", [{"channel": "chat"}, {"channel": "admin"}, {}])
async def test_ticket_request_validated(client: AsyncClient, user: User, body: dict[str, str]) -> None:
    response = await client.post("/api/ws/ticket", json=body, headers=auth_headers(user))

    assert response.status_code == 422


async def test_ticket_requires_auth(client: AsyncClient) -> None:
    assert (await client.post("/api/ws/ticket", json={"channel": "dashboard"})).status_code == 401


# ── WebSocket admission (Starlette TestClient; tickets written straight to fake Redis) ──

@pytest.fixture
def ws_client() -> Iterator[TestClient]:
    with TestClient(app) as tc:
        yield tc


def _ticket(user_id: UUID, channel: str = "dashboard", session_id: UUID | None = None) -> str:
    claims = TicketClaims(user_id=user_id, channel=channel, session_id=session_id)  # type: ignore[arg-type]
    return asyncio.run(issue_ticket(claims))


def _rejected(tc: TestClient, url: str) -> int:
    with pytest.raises(WebSocketDisconnect) as exc:
        with tc.websocket_connect(url) as ws:
            ws.receive_text()
    return exc.value.code


def test_ticket_admits_once(ws_client: TestClient) -> None:
    uid = uuid4()
    ticket = _ticket(uid)

    with ws_client.websocket_connect(f"/ws/dashboard/{uid}?ticket={ticket}") as ws:
        ws.send_text("ping")
        assert ws.receive_text() == "pong"

    assert _rejected(ws_client, f"/ws/dashboard/{uid}?ticket={ticket}") == 4002


def test_raw_jwt_rejected(ws_client: TestClient) -> None:
    uid = uuid4()
    token = create_access_token({"sub": str(uid)})

    assert _rejected(ws_client, f"/ws/dashboard/{uid}?token={token}") == 4001
    assert _rejected(ws_client, f"/ws/dashboard/{uid}?ticket={token}") == 4002


def test_dashboard_ticket_bound_to_user(ws_client: TestClient) -> None:
    assert _rejected(ws_client, f"/ws/dashboard/{uuid4()}?ticket={_ticket(uuid4())}") == 4003


def test_chat_ticket_bound_to_session(ws_client: TestClient) -> None:
    uid, sid = uuid4(), uuid4()

    assert _rejected(ws_client, f"/ws/chat/{uuid4()}?ticket={_ticket(uid, 'chat', sid)}") == 4003
    assert _rejected(ws_client, f"/ws/chat/{sid}?ticket={_ticket(uid)}") == 4003
    with ws_client.websocket_connect(f"/ws/chat/{sid}?ticket={_ticket(uid, 'chat', sid)}") as ws:
        ws.send_text("ping")
        assert ws.receive_text() == "pong"


def test_connection_cap_per_user(ws_client: TestClient) -> None:
    uid = uuid4()
    with (
        ws_client.websocket_connect(f"/ws/dashboard/{uid}?ticket={_ticket(uid)}"),
        ws_client.websocket_connect(f"/ws/dashboard/{uid}?ticket={_ticket(uid)}"),
        ws_client.websocket_connect(f"/ws/dashboard/{uid}?ticket={_ticket(uid)}"),
        ws_client.websocket_connect(f"/ws/dashboard/{uid}?ticket={_ticket(uid)}"),
        ws_client.websocket_connect(f"/ws/dashboard/{uid}?ticket={_ticket(uid)}"),
    ):
        assert _rejected(ws_client, f"/ws/dashboard/{uid}?ticket={_ticket(uid)}") == 4029


def test_error_in_loop_cleans_up(ws_client: TestClient) -> None:
    uid = uuid4()
    with ws_client.websocket_connect(f"/ws/dashboard/{uid}?ticket={_ticket(uid)}") as ws:
        ws.send_bytes(b"\x00")  # receive_text() raises on a binary frame

    with ws_client.websocket_connect(f"/ws/dashboard/{uid}?ticket={_ticket(uid)}") as ws:
        ws.send_text("ping")
        assert ws.receive_text() == "pong"
    assert manager.connection_count(str(uid)) == 0

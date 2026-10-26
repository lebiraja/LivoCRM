"""Redis-backed session context manager for the AI orchestrator.

Stores SessionContext objects in Redis only (SEC-20), keyed by owner and chat
session (`livocrm:ctx:<user>:<session>`) with an inactivity TTL, so state
survives restarts, is shared by every worker and cannot be read through
another user's session id. If Redis is unreachable a turn starts from a
fresh context and a warning is logged.
"""

from __future__ import annotations

import json
import logging
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from redis.exceptions import RedisError

from app.services.ai_engine.orchestrator import SessionContext, SessionState
from app.services.redis_client import get_redis

logger = logging.getLogger(__name__)

_TTL_SECONDS = 3600  # 1 hour — sessions expire after inactivity
_LOCK_TTL_MS = 30_000  # upper bound on one chat turn holding the session lock


def _key(user_id: UUID, session_id: UUID) -> str:
    return f"livocrm:ctx:{user_id}:{session_id}"


def _serialize(ctx: SessionContext) -> str:
    """Serialize SessionContext to JSON for Redis storage."""
    return json.dumps({
        "state": ctx.state.value,
        "intent": ctx.intent.value if ctx.intent else None,
        "collected_data": ctx.collected_data,
        "missing_required": ctx.missing_required,
        "history": ctx.history[-20:],  # Keep last 20 messages to limit size
        "last_saved_entity": ctx.last_saved_entity,
    })


def _deserialize(data: str) -> SessionContext:
    """Deserialize JSON from Redis back into a SessionContext."""
    from app.services.ai_engine.intent_classifier import Intent
    obj = json.loads(data)
    ctx = SessionContext()
    ctx.state = SessionState(obj.get("state", "IDLE"))
    intent_str = obj.get("intent")
    ctx.intent = Intent(intent_str) if intent_str else None
    ctx.collected_data = obj.get("collected_data", {})
    ctx.missing_required = obj.get("missing_required", [])
    ctx.history = obj.get("history", [])
    ctx.last_saved_entity = obj.get("last_saved_entity")
    return ctx


async def get_context(user_id: UUID, session_id: UUID) -> SessionContext:
    """Get the user's context for a chat session, or a fresh one."""
    try:
        data = await get_redis().get(_key(user_id, session_id))
    except RedisError:
        logger.warning("Redis read failed for session %s; starting a fresh context", session_id)
        return SessionContext()
    return _deserialize(data) if data else SessionContext()


async def _save_context(user_id: UUID, session_id: UUID, ctx: SessionContext) -> None:
    """Persist the context after mutations (refreshes the TTL)."""
    try:
        await get_redis().set(_key(user_id, session_id), _serialize(ctx), ex=_TTL_SECONDS)
    except RedisError:
        logger.warning("Redis write failed for session %s", session_id)


async def clear_context(user_id: UUID, session_id: UUID) -> None:
    """Remove a session context (e.g., when session is closed)."""
    try:
        await get_redis().delete(_key(user_id, session_id))
    except RedisError:
        logger.warning("Redis delete failed for session %s", session_id)


class SessionBusyError(Exception):
    """Another chat turn for the same session is still running."""


@asynccontextmanager
async def session_lock(session_id: UUID) -> AsyncIterator[None]:
    """Serialise chat turns per session (SEC-08): SET NX PX, deleted only by its owner.

    Fails open with a warning when Redis is unreachable, like the rate limiter.
    """
    client = get_redis()
    key = f"livocrm:lock:chat:{session_id}"
    token = secrets.token_hex(8)
    try:
        acquired = await client.set(key, token, nx=True, px=_LOCK_TTL_MS)
    except RedisError:
        logger.warning("Chat lock skipped for session %s: Redis unavailable", session_id)
        acquired = None
    else:
        if not acquired:
            raise SessionBusyError
    try:
        yield
    finally:
        if acquired:
            async with client.pipeline() as pipe:
                await pipe.watch(key)
                if await pipe.get(key) == token:
                    pipe.multi()
                    pipe.delete(key)
                    await pipe.execute()


async def reset_context(
    user_id: UUID,
    session_id: UUID,
    old_ctx: SessionContext,
    *,
    last_saved_entity: dict | None = None,
) -> SessionContext:
    """Reset a session context to IDLE while preserving conversation history.

    After saving an entity, we clear the extraction state but keep:
    - Conversation history (so the AI remembers the conversation)
    - Last saved entity info (so the user can immediately follow up)
    """
    ctx = SessionContext()
    ctx.history = old_ctx.history[-20:]  # Preserve conversation history
    ctx.last_saved_entity = last_saved_entity
    await _save_context(user_id, session_id, ctx)
    return ctx

"""Redis-backed session context manager for the AI orchestrator.

Stores SessionContext objects keyed by chat session UUID in Redis,
so conversation state survives container restarts.
Falls back to in-memory storage if Redis is unavailable.
"""

from __future__ import annotations

import json
import logging
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.config import settings
from app.services.ai_engine.orchestrator import SessionContext, SessionState
from app.services.redis_client import get_redis

logger = logging.getLogger(__name__)

# Redis prefix to namespace session keys
_REDIS_PREFIX = "livocrm:session:"
_TTL_SECONDS = 3600  # 1 hour — sessions expire after inactivity
_LOCK_TTL_MS = 30_000  # upper bound on one chat turn holding the session lock

# Connect to Redis (initialized lazily)
_redis: redis.Redis | None = None
_redis_available = False


async def _init_redis() -> None:
    """Initialize Redis connection."""
    global _redis, _redis_available
    try:
        _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await _redis.ping()
        _redis_available = True
        logger.info("Session manager connected to Redis")
    except Exception as e:
        _redis = None
        _redis_available = False
        logger.warning("Redis unavailable for session manager — using in-memory fallback: %s", str(e))


# Fallback in-memory store
_context_store: dict[UUID, SessionContext] = {}


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


async def get_context(session_id: UUID) -> SessionContext:
    """Get or create a SessionContext for a chat session."""
    global _redis
    if not _redis_available and _redis is None:
        await _init_redis()

    sid = str(session_id)

    if _redis_available and _redis:
        try:
            data = await _redis.get(f"{_REDIS_PREFIX}{sid}")
            if data:
                return _deserialize(data)
        except Exception:
            logger.warning("Redis read failed for session %s", sid)

    # Fallback to in-memory
    if session_id not in _context_store:
        _context_store[session_id] = SessionContext()
    return _context_store[session_id]


async def _save_context(session_id: UUID, ctx: SessionContext) -> None:
    """Persist the context after mutations."""
    global _redis
    if not _redis_available and _redis is None:
        await _init_redis()

    sid = str(session_id)

    if _redis_available and _redis:
        try:
            await _redis.setex(f"{_REDIS_PREFIX}{sid}", _TTL_SECONDS, _serialize(ctx))
        except Exception:
            logger.warning("Redis write failed for session %s", sid)

    # Always update in-memory too (for current process)
    _context_store[session_id] = ctx


async def clear_context(session_id: UUID) -> None:
    """Remove a session context (e.g., when session is closed)."""
    global _redis
    if not _redis_available and _redis is None:
        await _init_redis()

    sid = str(session_id)
    _context_store.pop(session_id, None)

    if _redis_available and _redis:
        try:
            await _redis.delete(f"{_REDIS_PREFIX}{sid}")
        except Exception:
            logger.warning("Redis delete failed for session %s", sid)


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
    await _save_context(session_id, ctx)
    return ctx

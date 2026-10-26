"""Shared async Redis client (lazy, one per process)."""

from __future__ import annotations

import redis.asyncio as redis

from app.config import settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Return the process-wide client; short socket timeouts so callers fail fast when Redis is down."""
    global _client
    if _client is None:
        _client = redis.from_url(
            settings.REDIS_URL, decode_responses=True, socket_connect_timeout=1, socket_timeout=1
        )
    return _client

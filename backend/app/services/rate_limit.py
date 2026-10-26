"""Redis fixed-window rate limits as FastAPI dependencies (SEC-03).

Usage::

    @router.post("/login", dependencies=[Depends(rate_limit("login", 5, 60, login_key))])

The key function is itself a dependency, so it can use the parsed body or the
current user. Over the limit -> 429 with Retry-After. If Redis is down the
request is allowed and a warning is logged (fail open); nginx `limit_req` is
the second layer.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, Request, status
from redis.exceptions import RedisError

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import LoginRequest
from app.services.redis_client import get_redis

logger = logging.getLogger(__name__)

_PREFIX = "livocrm:rl:"


def client_ip(request: Request) -> str:
    # uvicorn --proxy-headers resolves X-Forwarded-For from nginx into request.client
    return request.client.host if request.client else "unknown"


async def login_key(body: LoginRequest, request: Request) -> str:
    return f"{client_ip(request)}:{body.email}"


async def user_key(user: User = Depends(get_current_user)) -> str:
    return str(user.id)


def rate_limit(
    scope: str, limit: int, window_seconds: int, key: Callable[..., str | Awaitable[str]]
) -> Callable[[str], Awaitable[None]]:
    async def dependency(identity: str = Depends(key)) -> None:
        redis_key = f"{_PREFIX}{scope}:{identity}"
        try:
            async with get_redis().pipeline(transaction=True) as pipe:
                pipe.incr(redis_key)
                pipe.expire(redis_key, window_seconds, nx=True)
                count, _ = await pipe.execute()
                retry_after = await get_redis().ttl(redis_key) if count > limit else 0
        except RedisError:
            logger.warning("Rate limit check skipped for %s: Redis unavailable", scope)
            return
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests, try again later",
                headers={"Retry-After": str(max(retry_after, 1))},
            )

    return dependency

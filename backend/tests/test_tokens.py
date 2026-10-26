"""SEC-11/16: PyJWT access tokens carry iat/jti and reject tampering, expiry and alg=none."""

from __future__ import annotations

import base64
import json
from collections.abc import Awaitable, Callable
from datetime import timedelta

import jwt
import pytest
from httpx import AsyncClient

from app.config import settings
from app.models.user import User
from app.services.auth_service import create_access_token, verify_token


def _b64(data: dict[str, object]) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


def test_token_has_iat_and_unique_jti() -> None:
    first = jwt.decode(create_access_token({"sub": "x"}), settings.SECRET_KEY, algorithms=["HS256"])
    second = jwt.decode(create_access_token({"sub": "x"}), settings.SECRET_KEY, algorithms=["HS256"])

    assert {"sub", "exp", "iat", "jti"} <= first.keys()
    assert first["jti"] != second["jti"]


@pytest.fixture
async def user(make_user: Callable[..., Awaitable[User]]) -> User:
    return await make_user()


def _bad_tokens(user: User) -> dict[str, str]:
    sub = str(user.id)
    good = create_access_token({"sub": sub})
    head, payload, sig = good.split(".")
    return {
        "expired": create_access_token({"sub": sub}, expires_delta=timedelta(seconds=-5)),
        "tampered": f"{head}.{_b64({'sub': sub, 'exp': 9999999999, 'iat': 1})}.{sig}",
        "alg_none": f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{payload}.",
        "wrong_key": jwt.encode({"sub": sub, "exp": 9999999999, "iat": 1}, "k" * 40, algorithm="HS256"),
        "no_iat": jwt.encode({"sub": sub, "exp": 9999999999}, settings.SECRET_KEY, algorithm="HS256"),
    }


@pytest.mark.parametrize("case", ["expired", "tampered", "alg_none", "wrong_key", "no_iat"])
async def test_bad_token_is_401(client: AsyncClient, user: User, case: str) -> None:
    token = _bad_tokens(user)[case]

    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert verify_token(token) is None
    assert response.status_code == 401

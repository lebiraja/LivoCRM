"""Authentication helpers — password hashing & JWT creation / verification."""

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings


# ── Password ────────────────────────────────────────────────────────────────

def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# Checked against when the email is unknown so login timing does not reveal accounts
DUMMY_HASH = hash_password("dummy-password-for-timing")


# ── JWT ────────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    # jti identifies one token (for a future deny-list on logout)
    to_encode.update({"exp": expire, "iat": now, "jti": secrets.token_hex(16)})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM], options={"require": ["exp", "iat"]}
        )
    except jwt.InvalidTokenError:
        return None

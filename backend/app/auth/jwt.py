"""JWT issuing/verification and password hashing helpers.

Centralizes everything token-shaped so `app.dependencies.get_current_user`
and `app.services.auth_service` share one source of truth for how tokens
are minted and read. Passwords are hashed with bcrypt via passlib per
CLAUDE.md ("never store passwords in plain text").
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TokenType = Literal["access", "refresh", "password_reset"]


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(subject: str, token_type: TokenType, expires_delta: timedelta) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(subject: str) -> str:
    """Mint a short-lived access token (expires per `ACCESS_TOKEN_EXPIRE_MINUTES`)."""
    settings = get_settings()
    return _create_token(
        subject, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )


def create_refresh_token(subject: str) -> str:
    """Mint a long-lived refresh token (expires per `REFRESH_TOKEN_EXPIRE_DAYS`)."""
    settings = get_settings()
    return _create_token(
        subject, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )


def create_password_reset_token(subject: str) -> str:
    """Mint a short-lived (30 min) password-reset token.

    Stateless JWT, not stored/single-use-enforced in the DB — acceptable
    for MVP since the window is short, but note it is technically replayable
    within that window if leaked before use.
    """
    return _create_token(subject, "password_reset", timedelta(minutes=30))


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT's signature/expiry. Returns `None` if invalid."""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        logger.info("JWT decode failed: %s", exc)
        return None


def verify_token(token: str, expected_type: TokenType) -> dict[str, Any] | None:
    """Decode a token and ensure it is of `expected_type` ("access" or "refresh")."""
    payload = decode_token(token)
    if payload is None:
        return None
    if payload.get("type") != expected_type:
        logger.info("Token type mismatch: expected=%s got=%s", expected_type, payload.get("type"))
        return None
    return payload

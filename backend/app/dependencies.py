"""Shared FastAPI dependencies.

`get_current_user` decodes the bearer access token (via `app.auth.jwt`)
and resolves its `sub` claim into a real `app.models.user.User` ORM row —
every Phase 2 module depends on a real `User`, not a raw claims dict.
"""
from __future__ import annotations

import logging

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.jwt import verify_token
from app.database import get_db
from app.exceptions import UnauthorizedError
from app.models.user import User

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

__all__ = ["get_current_admin_user", "get_current_user", "get_db", "oauth2_scheme"]


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode the JWT access token and return the corresponding active `User`.

    Raises `UnauthorizedError` (-> HTTP 401) if the token is missing,
    invalid/expired, not an access token, references a user that no longer
    exists, or the user has been deactivated.
    """
    if token is None:
        raise UnauthorizedError("Missing authentication token")

    payload = verify_token(token, expected_type="access")
    if payload is None:
        raise UnauthorizedError("Invalid or expired token")

    subject = payload.get("sub")
    if subject is None:
        raise UnauthorizedError("Token missing subject claim")

    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise UnauthorizedError("Invalid token subject") from exc

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    return user


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to have `is_admin = True`. Used by Admin Panel routes."""
    if not current_user.is_admin:
        raise UnauthorizedError("Admin privileges required")
    return current_user

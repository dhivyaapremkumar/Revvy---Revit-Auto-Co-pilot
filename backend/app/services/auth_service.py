"""Business logic for the Auth module.

Routers stay thin (parse request -> call service -> shape response);
all DB reads/writes and token bookkeeping for register/login/refresh/logout
live here.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.auth.jwt import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.config import get_settings
from app.exceptions import ConflictError, UnauthorizedError, ValidationError
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenResponse, UserUpdateRequest
from app.services.email_service import send_password_reset_email

logger = logging.getLogger(__name__)


def register_user(db: Session, data: RegisterRequest) -> User:
    """Create a new `User` with a bcrypt-hashed password.

    Raises `ConflictError` if the email is already registered.
    """
    existing = db.query(User).filter(User.email == data.email).first()
    if existing is not None:
        raise ConflictError("An account with this email already exists")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Registered new user id=%s", user.id)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """Verify credentials and return the matching active `User`.

    Raises `UnauthorizedError` for any invalid-credential or inactive-user
    case (deliberately not distinguishing "no such email" from "wrong
    password" in the response, to avoid user enumeration).
    """
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedError("This account has been deactivated")
    return user


def _persist_refresh_token(db: Session, user_id: int, token: str) -> RefreshToken:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    record = RefreshToken(user_id=user_id, token=token, expires_at=expires_at, revoked=False)
    db.add(record)
    db.commit()
    return record


def issue_tokens(db: Session, user: User) -> TokenResponse:
    """Issue a fresh access+refresh token pair for `user` and persist the refresh token."""
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    _persist_refresh_token(db, user.id, refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


def refresh_access_token(db: Session, refresh_token: str) -> TokenResponse:
    """Validate a refresh token and rotate it for a new access+refresh pair.

    Raises `UnauthorizedError` if the token is invalid, expired, revoked, or
    unknown to the database (e.g. already used once, since we rotate).
    """
    payload = verify_token(refresh_token, expected_type="refresh")
    if payload is None:
        raise UnauthorizedError("Invalid or expired refresh token")

    record = db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
    if record is None or record.revoked:
        raise UnauthorizedError("Refresh token has been revoked or does not exist")
    if record.expires_at <= datetime.now(UTC):
        raise UnauthorizedError("Refresh token has expired")

    user = db.query(User).filter(User.id == record.user_id).first()
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    # Rotate: revoke the presented token, issue a brand new pair.
    record.revoked = True
    db.add(record)
    db.commit()

    return issue_tokens(db, user)


def revoke_refresh_token(db: Session, refresh_token: str) -> None:
    """Revoke a refresh token (logout). Silently no-ops if it's already gone/revoked."""
    record = db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
    if record is not None and not record.revoked:
        record.revoked = True
        db.add(record)
        db.commit()


def update_profile(db: Session, user: User, data: UserUpdateRequest) -> User:
    """Apply self-service profile updates to `user`."""
    if data.full_name is not None:
        user.full_name = data.full_name
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


async def request_password_reset(db: Session, email: str) -> None:
    """Email a password-reset link if `email` matches an active account.

    Always returns `None` regardless of whether the email matches, to avoid
    leaking which addresses are registered (user enumeration).
    """
    settings = get_settings()
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        logger.info("Password reset requested for unknown/inactive email")
        return
    reset_token = create_password_reset_token(str(user.id))
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    await send_password_reset_email(to=user.email, reset_token=reset_token, reset_url=reset_url)


def reset_password(db: Session, token: str, new_password: str) -> None:
    """Consume a password-reset token and set a new password.

    Raises `UnauthorizedError` if the token is invalid/expired/wrong-type,
    or `ValidationError` if the user no longer exists/is inactive. Revokes
    all existing refresh tokens so other sessions are logged out.
    """
    payload = verify_token(token, expected_type="password_reset")
    if payload is None:
        raise UnauthorizedError("Invalid or expired password reset link")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first() if user_id else None
    if user is None or not user.is_active:
        raise ValidationError("Account no longer exists or is inactive")

    user.hashed_password = hash_password(new_password)
    db.add(user)
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False)).update(
        {"revoked": True}
    )
    db.commit()
    logger.info("Password reset completed for user id=%s", user.id)

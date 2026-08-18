"""Auth module endpoints: register, login, refresh, logout, profile.

Rate limiting: `register` and `login` are throttled via `slowapi`
(in-memory, per-client-IP — see `app.rate_limit` for the storage-backend
tradeoff note) to blunt credential-stuffing/signup-spam attempts:
- register: 5 requests/minute/IP
- login: 10 requests/minute/IP
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.rate_limit import limiter
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    UserUpdateRequest,
)
from app.services import auth_service
from app.services.email_service import send_welcome_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    data: RegisterRequest,
    db: Session = Depends(get_db),
) -> User:
    """Create a new account and send a welcome email."""
    user = auth_service.register_user(db, data)
    await send_welcome_email(to=user.email, full_name=user.full_name)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    data: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email+password and return an access/refresh token pair."""
    user = auth_service.authenticate_user(db, data.email, data.password)
    return auth_service.issue_tokens(db, user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Exchange a valid, unexpired, unrevoked refresh token for a new token pair."""
    return auth_service.refresh_access_token(db, data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: LogoutRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> None:
    """Revoke a refresh token, ending that session."""
    auth_service.revoke_refresh_token(db, data.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> User:
    """Return the currently authenticated user."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    """Update the current user's own profile fields."""
    return auth_service.update_profile(db, current_user, data)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> None:
    """Email a password-reset link if the address matches an active account.

    Always returns 204 regardless of whether the email matches, to avoid
    leaking which addresses are registered.
    """
    await auth_service.request_password_reset(db, data.email)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> None:
    """Consume a password-reset token (from the emailed link) and set a new password."""
    auth_service.reset_password(db, data.token, data.new_password)

"""Pydantic schemas for the Auth module."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Payload for `POST /api/v1/auth/register`."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=150)


class LoginRequest(BaseModel):
    """Payload for `POST /api/v1/auth/login`.

    Plain JSON body (rather than `OAuth2PasswordRequestForm`) since REVVY's
    clients are the React SPA and the pyRevit add-in, both of which speak
    JSON natively — see BACKEND-AGENT deviation note in the task report.
    """

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Access + refresh token pair returned by register/login/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Payload for `POST /api/v1/auth/refresh`."""

    refresh_token: str


class LogoutRequest(BaseModel):
    """Payload for `POST /api/v1/auth/logout`."""

    refresh_token: str


class UserResponse(BaseModel):
    """Public-facing representation of a `User`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None
    is_active: bool
    is_verified: bool
    is_admin: bool
    created_at: datetime


class UserUpdateRequest(BaseModel):
    """Payload for `PUT /api/v1/auth/me` — self-service profile fields only."""

    full_name: str | None = Field(default=None, max_length=150)


class ForgotPasswordRequest(BaseModel):
    """Payload for `POST /api/v1/auth/forgot-password`."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Payload for `POST /api/v1/auth/reset-password`."""

    token: str
    new_password: str = Field(min_length=8, max_length=128)

"""Tests for the Auth module: register, login, refresh, logout, profile,
and the forgot-password/reset-password flow.
"""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from app.services import auth_service
from tests.conftest import make_expired_token

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


async def test_register_success(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "Password123!", "full_name": "New User"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "new@example.com"
    assert body["full_name"] == "New User"
    assert body["is_active"] is True
    assert body["is_admin"] is False
    assert "hashed_password" not in body


async def test_register_duplicate_email_conflicts(client):
    payload = {"email": "dupe@example.com", "password": "Password123!"}
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409
    assert second.json()["code"] == "CONFLICT"


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


async def test_login_success(client, auth_user):
    resp = client.post(
        "/api/v1/auth/login", json={"email": auth_user["email"], "password": auth_user["password"]}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_wrong_password(client, auth_user):
    resp = client.post(
        "/api/v1/auth/login", json={"email": auth_user["email"], "password": "wrong-password"}
    )
    assert resp.status_code == 401


async def test_login_inactive_user(client, db, auth_user):
    from app.models.user import User

    db.query(User).filter(User.id == auth_user["id"]).update({"is_active": False})
    db.commit()

    resp = client.post(
        "/api/v1/auth/login", json={"email": auth_user["email"], "password": auth_user["password"]}
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


async def test_refresh_success(client, auth_user):
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": auth_user["refresh_token"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"] != auth_user["refresh_token"]  # rotated


async def test_refresh_revoked_token_rejected(client, auth_user):
    logout_resp = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": auth_user["refresh_token"]},
        headers=auth_user["headers"],
    )
    assert logout_resp.status_code == 204

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": auth_user["refresh_token"]})
    assert resp.status_code == 401


async def test_refresh_expired_token_rejected(client, auth_user):
    expired = make_expired_token(str(auth_user["id"]), "refresh")
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": expired})
    assert resp.status_code == 401


async def test_refresh_reused_token_rejected_after_rotation(client, auth_user):
    """Refresh tokens rotate on use -- the presented token can't be replayed."""
    first = client.post("/api/v1/auth/refresh", json={"refresh_token": auth_user["refresh_token"]})
    assert first.status_code == 200

    replay = client.post("/api/v1/auth/refresh", json={"refresh_token": auth_user["refresh_token"]})
    assert replay.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


async def test_logout_requires_auth(client, auth_user):
    resp = client.post("/api/v1/auth/logout", json={"refresh_token": auth_user["refresh_token"]})
    assert resp.status_code == 401


async def test_logout_success(client, auth_user):
    resp = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": auth_user["refresh_token"]},
        headers=auth_user["headers"],
    )
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Me / update profile
# ---------------------------------------------------------------------------


async def test_me_unauthorized(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_me_authorized(client, auth_user):
    resp = client.get("/api/v1/auth/me", headers=auth_user["headers"])
    assert resp.status_code == 200
    assert resp.json()["email"] == auth_user["email"]


async def test_update_me(client, auth_user):
    resp = client.put(
        "/api/v1/auth/me", json={"full_name": "Updated Name"}, headers=auth_user["headers"]
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Updated Name"


# ---------------------------------------------------------------------------
# Forgot password / reset password
# ---------------------------------------------------------------------------


async def test_forgot_and_reset_password_flow(client, auth_user, monkeypatch):
    captured: dict[str, str] = {}

    async def fake_send_password_reset_email(*, to: str, reset_token: str, reset_url: str) -> None:
        captured["to"] = to
        captured["reset_url"] = reset_url

    monkeypatch.setattr(auth_service, "send_password_reset_email", fake_send_password_reset_email)

    forgot_resp = client.post("/api/v1/auth/forgot-password", json={"email": auth_user["email"]})
    assert forgot_resp.status_code == 204
    assert captured["to"] == auth_user["email"]

    token = parse_qs(urlparse(captured["reset_url"]).query)["token"][0]

    reset_resp = client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "NewPassword456!"}
    )
    assert reset_resp.status_code == 204

    old_login = client.post(
        "/api/v1/auth/login", json={"email": auth_user["email"], "password": auth_user["password"]}
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login", json={"email": auth_user["email"], "password": "NewPassword456!"}
    )
    assert new_login.status_code == 200


async def test_forgot_password_unknown_email_still_returns_204(client):
    """Never leak whether an email is registered (user enumeration defense)."""
    resp = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert resp.status_code == 204


async def test_reset_password_garbage_token_rejected(client):
    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "not-a-real-token", "new_password": "NewPassword456!"},
    )
    assert resp.status_code == 401


async def test_reset_password_expired_token_rejected(client, auth_user):
    expired = make_expired_token(str(auth_user["id"]), "password_reset")
    resp = client.post(
        "/api/v1/auth/reset-password", json={"token": expired, "new_password": "NewPassword456!"}
    )
    assert resp.status_code == 401


async def test_reset_password_revokes_existing_refresh_tokens(client, auth_user, monkeypatch):
    """Per auth_service.reset_password: all other sessions are logged out."""

    async def fake_send(*, to: str, reset_token: str, reset_url: str) -> None:
        captured["reset_url"] = reset_url

    captured: dict[str, str] = {}
    monkeypatch.setattr(auth_service, "send_password_reset_email", fake_send)

    client.post("/api/v1/auth/forgot-password", json={"email": auth_user["email"]})
    token = parse_qs(urlparse(captured["reset_url"]).query)["token"][0]
    client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "NewPassword456!"})

    refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": auth_user["refresh_token"]})
    assert refresh_resp.status_code == 401

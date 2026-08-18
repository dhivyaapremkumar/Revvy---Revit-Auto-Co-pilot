"""Tests for the Admin Panel + Analytics module."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio

_REQUIRED_STATS_FIELDS = {
    "total_users",
    "active_users",
    "code_queries_per_day",
    "model_queries_per_day",
    "code_queries_total",
    "model_queries_total",
    "most_cited_sections",
}


async def test_non_admin_gets_401_on_all_admin_routes(client, auth_user):
    assert client.get("/api/v1/admin/users", headers=auth_user["headers"]).status_code == 401
    assert (
        client.put(
            "/api/v1/admin/users/1", json={"is_active": False}, headers=auth_user["headers"]
        ).status_code
        == 401
    )
    assert client.get("/api/v1/admin/stats", headers=auth_user["headers"]).status_code == 401
    assert client.get("/api/v1/admin/code-documents", headers=auth_user["headers"]).status_code == 401


async def test_admin_routes_require_auth_entirely(client):
    assert client.get("/api/v1/admin/users").status_code == 401
    assert client.get("/api/v1/admin/stats").status_code == 401


async def test_admin_can_list_users(client, admin_user, auth_user):
    resp = client.get("/api/v1/admin/users", headers=admin_user["headers"])
    assert resp.status_code == 200
    emails = {u["email"] for u in resp.json()}
    assert admin_user["email"] in emails
    assert auth_user["email"] in emails


async def test_admin_can_update_user(client, admin_user, auth_user):
    resp = client.put(
        f"/api/v1/admin/users/{auth_user['id']}",
        json={"is_active": False, "is_verified": True},
        headers=admin_user["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_active"] is False
    assert body["is_verified"] is True

    # Deactivated user can no longer log in.
    login_resp = client.post(
        "/api/v1/auth/login", json={"email": auth_user["email"], "password": auth_user["password"]}
    )
    assert login_resp.status_code == 401


async def test_admin_update_nonexistent_user_404s(client, admin_user):
    resp = client.put(
        "/api/v1/admin/users/999999", json={"is_active": False}, headers=admin_user["headers"]
    )
    assert resp.status_code == 404


async def test_admin_stats_has_exact_field_names(client, admin_user):
    resp = client.get("/api/v1/admin/stats", headers=admin_user["headers"])
    assert resp.status_code == 200
    body = resp.json()
    assert _REQUIRED_STATS_FIELDS <= set(body.keys())
    assert body["total_users"] >= 1
    assert isinstance(body["most_cited_sections"], list)


async def test_admin_can_list_code_documents(client, admin_user, fake_llm):
    client.post(
        "/api/v1/code-documents",
        files={"file": ("tncdbr.txt", b"Section 1 General provisions.", "text/plain")},
        data={
            "title": "TNCDBR 2019",
            "source_type": "tncdbr",
            "jurisdiction": "Tamil Nadu",
            "version": "2019",
        },
        headers=admin_user["headers"],
    )

    resp = client.get("/api/v1/admin/code-documents", headers=admin_user["headers"])
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["chunk_count"] >= 1

"""Tests for the Chat Copilot module."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_create_session(client, auth_user):
    resp = client.post(
        "/api/v1/chat/sessions",
        json={"title": "My first session", "revit_project_name": "Tower.rvt"},
        headers=auth_user["headers"],
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == "My first session"
    assert body["revit_project_name"] == "Tower.rvt"


async def test_list_sessions(client, auth_user):
    client.post("/api/v1/chat/sessions", json={"title": "Session A"}, headers=auth_user["headers"])
    client.post("/api/v1/chat/sessions", json={"title": "Session B"}, headers=auth_user["headers"])

    resp = client.get("/api/v1/chat/sessions", headers=auth_user["headers"])
    assert resp.status_code == 200
    titles = {s["title"] for s in resp.json()}
    assert titles == {"Session A", "Session B"}


async def test_get_session_detail_with_messages(client, auth_user, fake_llm):
    create_resp = client.post(
        "/api/v1/chat/sessions", json={"title": "Detail test"}, headers=auth_user["headers"]
    )
    session_id = create_resp.json()["id"]

    fake_llm.plain_chat_reply = "Here is some Revit advice."
    post_resp = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "How do I model a curtain wall?"},
        headers=auth_user["headers"],
    )
    assert post_resp.status_code == 201, post_resp.text
    assert post_resp.json()["role"] == "assistant"
    assert post_resp.json()["content"] == "Here is some Revit advice."

    detail_resp = client.get(f"/api/v1/chat/sessions/{session_id}", headers=auth_user["headers"])
    assert detail_resp.status_code == 200
    messages = detail_resp.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "How do I model a curtain wall?"
    assert messages[1]["role"] == "assistant"


async def test_post_message_routes_code_question_through_rag(client, auth_user, fake_llm, seed_code_chunk):
    """A message that looks like a code-compliance question is answered via
    Code-RAG (cited, grounded) rather than a freeform chat completion."""
    create_resp = client.post(
        "/api/v1/chat/sessions", json={"title": "Compliance Q"}, headers=auth_user["headers"]
    )
    session_id = create_resp.json()["id"]

    fake_llm.rag_answer = "The required setback is 3 meters (Section 4.2)."
    post_resp = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "What is the building code setback requirement?"},
        headers=auth_user["headers"],
    )
    assert post_resp.status_code == 201
    assert "Section 4.2" in post_resp.json()["content"]


async def test_delete_session(client, auth_user):
    create_resp = client.post(
        "/api/v1/chat/sessions", json={"title": "To delete"}, headers=auth_user["headers"]
    )
    session_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/api/v1/chat/sessions/{session_id}", headers=auth_user["headers"])
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/api/v1/chat/sessions/{session_id}", headers=auth_user["headers"])
    assert get_resp.status_code == 404


async def test_user_cannot_access_another_users_session(client, auth_user, other_user):
    create_resp = client.post(
        "/api/v1/chat/sessions", json={"title": "Private"}, headers=auth_user["headers"]
    )
    session_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/chat/sessions/{session_id}", headers=other_user["headers"])
    assert resp.status_code == 404

    delete_resp = client.delete(f"/api/v1/chat/sessions/{session_id}", headers=other_user["headers"])
    assert delete_resp.status_code == 404

    message_resp = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "hi"},
        headers=other_user["headers"],
    )
    assert message_resp.status_code == 404


async def test_chat_sessions_require_auth(client):
    assert client.get("/api/v1/chat/sessions").status_code == 401
    assert client.post("/api/v1/chat/sessions", json={"title": "x"}).status_code == 401

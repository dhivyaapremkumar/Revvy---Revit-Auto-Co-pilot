"""Tests for the Code-RAG module: ingestion, listing/deletion, and cited
Q&A search with a deterministic embedding threshold."""
from __future__ import annotations

import pytest

from tests.conftest import DEFAULT_VECTOR, ORTHOGONAL_VECTOR

pytestmark = pytest.mark.asyncio


def _upload(client, headers, *, content: bytes = b"Section 4.2 Setback requirements: 3 meters minimum."):
    return client.post(
        "/api/v1/code-documents",
        files={"file": ("tncdbr.txt", content, "text/plain")},
        data={
            "title": "TNCDBR 2019",
            "source_type": "tncdbr",
            "jurisdiction": "Tamil Nadu",
            "version": "2019",
        },
        headers=headers,
    )


async def test_upload_document_is_chunked_and_embedded(client, admin_user, fake_llm):
    resp = _upload(client, admin_user["headers"])
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == "TNCDBR 2019"
    assert body["source_type"] == "tncdbr"
    assert body["chunk_count"] >= 1


async def test_upload_requires_admin(client, auth_user, fake_llm):
    """Code-document management is admin-only: this corpus is cited as
    authoritative by every user's compliance checks and Code-RAG answers."""
    resp = _upload(client, auth_user["headers"])
    assert resp.status_code == 401


async def test_list_and_delete_require_admin(client, auth_user, admin_user, fake_llm):
    upload_resp = _upload(client, admin_user["headers"])
    document_id = upload_resp.json()["id"]

    assert client.get("/api/v1/code-documents", headers=auth_user["headers"]).status_code == 401
    assert (
        client.delete(f"/api/v1/code-documents/{document_id}", headers=auth_user["headers"]).status_code
        == 401
    )


async def test_upload_unsupported_file_type_rejected(client, admin_user, fake_llm):
    resp = client.post(
        "/api/v1/code-documents",
        files={"file": ("doc.docx", b"binary junk", "application/octet-stream")},
        data={
            "title": "Bad doc",
            "source_type": "tncdbr",
            "jurisdiction": "Tamil Nadu",
            "version": "2019",
        },
        headers=admin_user["headers"],
    )
    assert resp.status_code == 400


async def test_list_documents(client, admin_user, fake_llm):
    _upload(client, admin_user["headers"])
    resp = client.get("/api/v1/code-documents", headers=admin_user["headers"])
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_delete_document_cascades_chunks(client, admin_user, fake_llm):
    upload_resp = _upload(client, admin_user["headers"])
    document_id = upload_resp.json()["id"]

    delete_resp = client.delete(f"/api/v1/code-documents/{document_id}", headers=admin_user["headers"])
    assert delete_resp.status_code == 204

    list_resp = client.get("/api/v1/code-documents", headers=admin_user["headers"])
    assert list_resp.json() == []


async def test_query_returns_not_found_when_no_documents_ingested(client, auth_user, fake_llm):
    resp = client.post(
        "/api/v1/code-rag/query",
        json={"query": "What is the minimum setback?"},
        headers=auth_user["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is False
    assert body["citations"] == []
    assert "not" in body["answer"].lower() or "could not" in body["answer"].lower()


async def test_query_returns_cited_answer_when_relevant_chunk_exists(
    client, auth_user, fake_llm, seed_code_chunk
):
    fake_llm.rag_answer = "The minimum setback is 3 meters (Section 4.2)."
    resp = client.post(
        "/api/v1/code-rag/query",
        json={"query": "What is the minimum front setback?"},
        headers=auth_user["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is True
    assert len(body["citations"]) == 1
    citation = body["citations"][0]
    assert citation["section_reference"] == "Section 4.2"
    assert citation["chunk_id"] == seed_code_chunk.id
    assert "Section 4.2" in body["answer"]


async def test_query_returns_not_found_when_chunk_exists_but_below_threshold(
    client, auth_user, admin_user, fake_llm, db
):
    """A chunk exists, but its embedding is orthogonal to the query embedding
    (cosine similarity 0.0), which is below CODE_RAG_SIMILARITY_THRESHOLD
    (0.75) -- the "not found" response must still be returned rather than a
    guess grounded in an irrelevant chunk."""
    fake_llm.embedding_vector = list(DEFAULT_VECTOR)
    _upload(client, admin_user["headers"], content=b"Some unrelated section about fire exits.")

    fake_llm.embedding_vector = list(ORTHOGONAL_VECTOR)
    resp = client.post(
        "/api/v1/code-rag/query",
        json={"query": "What is the minimum setback?"},
        headers=auth_user["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is False
    assert body["citations"] == []


async def test_code_rag_requires_auth(client):
    assert client.get("/api/v1/code-documents").status_code == 401
    assert client.post("/api/v1/code-rag/query", json={"query": "x"}).status_code == 401

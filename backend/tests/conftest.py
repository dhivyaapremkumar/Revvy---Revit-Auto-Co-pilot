"""Shared pytest fixtures for the REVVY backend test suite.

Database strategy
------------------
Tests run against a real Postgres+pgvector instance (the same one started
via `docker compose up -d postgres`), but never against the `revvy` dev
database: a dedicated `revvy_test` database is created once per test
*session* (fast: the schema is only built once) and every table is
TRUNCATEd after each individual test function for isolation. This is
simpler and more robust than per-test transaction/SAVEPOINT rollback given
that application code calls `db.commit()` internally throughout (auth,
chat, design generation, ...), which would otherwise end an outer
transaction wrapper.

LLM mocking
-----------
`OPENAI_API_KEY` is a placeholder in this sandbox, so every test that
exercises a code path calling `app.services.llm_service` must go through
the `fake_llm` fixture, which monkeypatches `chat_completion`,
`create_embedding`, and `create_embeddings_batch` with deterministic fakes.
Callers reach these via the `llm_service` *module* (e.g.
`llm_service.chat_completion(...)`) rather than `from ... import
chat_completion`, so patching the module's attributes affects every
importer (rag_service, chat_service, model_query_service) in one place.
"""
from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models.code_chunk import EMBEDDING_DIMENSIONS, CodeChunk
from app.models.code_document import CodeDocument, CodeDocumentSourceType
from app.models.user import User
from app.rate_limit import limiter
from app.services import llm_service

# Import every model module so `Base.metadata` is fully populated before
# `create_all` runs (mirrors what `app.models.__init__` already does, but
# imported explicitly here for clarity of intent). NOTE: must not be spelled
# `import app.models` -- that rebinds the local name `app` to the package,
# clobbering the `from app.main import app` (FastAPI instance) import above.
from app import models as _all_models  # noqa: F401

settings = get_settings()

# ---------------------------------------------------------------------------
# Rate limiting: disabled for the whole test session. slowapi's in-memory
# limiter is keyed by client IP, and Starlette's TestClient always presents
# the same fake IP ("testclient") -- without this, the 5th `register` call or
# 10th `login` call across the *entire test session* would start returning
# 429s, since register/login fixtures are used pervasively across files.
# ---------------------------------------------------------------------------
limiter.enabled = False


def _swap_db_name(url: str, new_name: str) -> str:
    base, _, _ = url.rpartition("/")
    return f"{base}/{new_name}"


TEST_DB_NAME = "revvy_test"
TEST_DATABASE_URL = _swap_db_name(settings.DATABASE_URL, TEST_DB_NAME)
MAINTENANCE_DATABASE_URL = _swap_db_name(settings.DATABASE_URL, "postgres")

# A constant "matching" embedding vector and an orthogonal "non-matching"
# one, so tests can control cosine-similarity outcomes deterministically
# without a real embedding model. Cosine similarity between these two unit
# vectors is exactly 0.0, well under `CODE_RAG_SIMILARITY_THRESHOLD` (0.75).
DEFAULT_VECTOR: list[float] = [1.0] + [0.0] * (EMBEDDING_DIMENSIONS - 1)
ORTHOGONAL_VECTOR: list[float] = [0.0, 1.0] + [0.0] * (EMBEDDING_DIMENSIONS - 2)


@pytest.fixture(scope="session")
def test_engine():
    """Create the `revvy_test` database + full ORM schema once per session."""
    admin_engine = create_engine(MAINTENANCE_DATABASE_URL, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"'))
        conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin_engine.dispose()

    engine = create_engine(TEST_DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)

    yield engine

    engine.dispose()
    admin_engine = create_engine(MAINTENANCE_DATABASE_URL, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"'))
    admin_engine.dispose()


@pytest.fixture
def db(test_engine) -> Iterator[Session]:
    """A `Session` against the test DB. All tables are truncated afterwards."""
    session_factory = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        with test_engine.connect() as conn:
            table_names = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
            conn.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
            conn.commit()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    """A `TestClient` wired to use the `db` fixture's session for every request."""

    def _override_get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class FakeLLM:
    """Deterministic stand-in for `app.services.llm_service`.

    Branches its `chat_completion` response on a distinctive phrase from
    each call site's system prompt, so a single monkeypatched fixture can
    serve every module (chat, code-rag, model query) without positional
    call-order assumptions. Every attribute is mutable mid-test so
    individual tests can flip e.g. `fake_llm.rag_answer = "..."`.
    """

    def __init__(self) -> None:
        self.rag_answer = "The minimum setback is 3 meters (Section 4.2)."
        self.plain_chat_reply = "Sure -- here's some general Revit modeling help."
        self.model_query_reply = "There are 3 walls on Level 1 in the current snapshot."
        self.embedding_vector: list[float] = list(DEFAULT_VECTOR)
        self.calls: list[dict[str, Any]] = []

    async def chat_completion(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        self.calls.append({"messages": messages, "kwargs": kwargs})
        system = messages[0]["content"] if messages else ""
        if "compliance assistant" in system:
            return self.rag_answer
        if "read-only Revit model query assistant" in system:
            return self.model_query_reply
        return self.plain_chat_reply

    async def create_embedding(self, text_: str, **kwargs: Any) -> list[float]:
        return list(self.embedding_vector)

    async def create_embeddings_batch(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        return [list(self.embedding_vector) for _ in texts]


@pytest.fixture
def fake_llm(monkeypatch: pytest.MonkeyPatch) -> FakeLLM:
    """Monkeypatch `llm_service` module functions with deterministic fakes."""
    fake = FakeLLM()
    monkeypatch.setattr(llm_service, "chat_completion", fake.chat_completion)
    monkeypatch.setattr(llm_service, "create_embedding", fake.create_embedding)
    monkeypatch.setattr(llm_service, "create_embeddings_batch", fake.create_embeddings_batch)
    return fake


def _register_and_login(
    client: TestClient,
    db: Session,
    *,
    email: str,
    password: str = "Password123!",
    full_name: str = "Test User",
    is_admin: bool = False,
) -> dict[str, Any]:
    register_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert register_resp.status_code == 201, register_resp.text
    user_id = register_resp.json()["id"]

    if is_admin:
        db.query(User).filter(User.id == user_id).update({"is_admin": True})
        db.commit()

    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200, login_resp.text
    tokens = login_resp.json()

    return {
        "id": user_id,
        "email": email,
        "password": password,
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "headers": {"Authorization": f"Bearer {tokens['access_token']}"},
    }


@pytest.fixture
def auth_user(client: TestClient, db: Session) -> dict[str, Any]:
    """A registered + logged-in regular user. Returns id/tokens/auth headers."""
    return _register_and_login(client, db, email=f"user-{uuid.uuid4().hex[:10]}@example.com")


@pytest.fixture
def other_user(client: TestClient, db: Session) -> dict[str, Any]:
    """A second, distinct regular user -- for cross-user access-control tests."""
    return _register_and_login(client, db, email=f"other-{uuid.uuid4().hex[:10]}@example.com")


@pytest.fixture
def admin_user(client: TestClient, db: Session) -> dict[str, Any]:
    """A registered + logged-in user with `is_admin=True`."""
    return _register_and_login(
        client, db, email=f"admin-{uuid.uuid4().hex[:10]}@example.com", is_admin=True
    )


@pytest.fixture
def seed_code_chunk(db: Session, auth_user: dict[str, Any]) -> CodeChunk:
    """Seed one ingested `CodeDocument` + `CodeChunk` with `DEFAULT_VECTOR`.

    Any query embedded with `fake_llm.embedding_vector` left at its default
    will have cosine similarity 1.0 against this chunk (comfortably above
    `CODE_RAG_SIMILARITY_THRESHOLD`), letting tests exercise the "a relevant
    chunk was found" path deterministically.
    """
    document = CodeDocument(
        title="TNCDBR 2019",
        source_type=CodeDocumentSourceType.tncdbr,
        jurisdiction="Tamil Nadu",
        version="2019",
        uploaded_by=auth_user["id"],
        file_path="uploads/code_documents/seed.txt",
    )
    db.add(document)
    db.flush()
    chunk = CodeChunk(
        document_id=document.id,
        section_reference="Section 4.2",
        content="The minimum front setback for a residential plot is 3 meters.",
        embedding=list(DEFAULT_VECTOR),
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def make_expired_token(subject: str, token_type: str) -> str:
    """Craft a JWT of `token_type` for `subject` that already expired.

    Used to test the "expired token" branch of refresh/reset-password
    without waiting for a real token to age out.
    """
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now - timedelta(hours=1),
        "exp": now - timedelta(minutes=1),
        "jti": uuid.uuid4().hex,
    }
    return jose_jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

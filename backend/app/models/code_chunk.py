"""CodeChunk model — a chunk of a CodeDocument with its embedding vector.

Requires the Postgres `vector` extension (pgvector). The migration that
creates this table must run `CREATE EXTENSION IF NOT EXISTS vector;` first.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin

if TYPE_CHECKING:
    from app.models.code_document import CodeDocument

# text-embedding-3-small (OpenAI) produces 1536-dimensional embeddings.
EMBEDDING_DIMENSIONS = 1536


class CodeChunk(Base, CreatedAtMixin):
    """A retrievable, embedded section of a `CodeDocument` for RAG search."""

    __tablename__ = "code_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("code_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_reference: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS), nullable=False
    )

    document: Mapped[CodeDocument] = relationship(back_populates="chunks")

    __table_args__ = (
        # Mirrors the raw `CREATE INDEX ... USING hnsw` in the initial migration
        # so metadata and the live schema agree (otherwise autogenerate/`alembic
        # check` sees this index as untracked and proposes dropping it).
        Index(
            "ix_code_chunks_embedding_hnsw",
            embedding,
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

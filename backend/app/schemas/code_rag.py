"""Pydantic schemas for the Code-RAG module."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.code_document import CodeDocumentSourceType


class CodeDocumentResponse(BaseModel):
    """An ingested `CodeDocument`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source_type: CodeDocumentSourceType
    jurisdiction: str
    version: str
    uploaded_by: int
    file_path: str
    created_at: datetime
    chunk_count: int = 0


class CodeRagQueryRequest(BaseModel):
    """Payload for `POST /api/v1/code-rag/query`."""

    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class CodeRagCitation(BaseModel):
    """A single cited `CodeChunk` backing a RAG answer."""

    chunk_id: int
    document_id: int
    document_title: str
    section_reference: str
    content: str
    similarity: float


class CodeRagQueryResponse(BaseModel):
    """Cited answer returned by `POST /api/v1/code-rag/query`."""

    answer: str
    citations: list[CodeRagCitation]
    found: bool

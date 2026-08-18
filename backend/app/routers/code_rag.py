"""Code-RAG module endpoints.

Two distinct URL segments are served from this one router (no shared
prefix): `/code-documents` (ingestion/management) and `/code-rag/query`
(cited Q&A), matching PRPs/revvy-prp.md's Module 3 endpoint table exactly.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_admin_user, get_current_user
from app.exceptions import ValidationError
from app.models.code_chunk import CodeChunk
from app.models.code_document import CodeDocument, CodeDocumentSourceType
from app.models.user import User
from app.schemas.code_rag import (
    CodeDocumentResponse,
    CodeRagQueryRequest,
    CodeRagQueryResponse,
)
from app.services import rag_service

router = APIRouter(tags=["code-rag"])


def _to_document_response(db: Session, document: CodeDocument) -> CodeDocumentResponse:
    chunk_count = db.query(CodeChunk).filter(CodeChunk.document_id == document.id).count()
    return CodeDocumentResponse.model_validate(document, from_attributes=True).model_copy(
        update={"chunk_count": chunk_count}
    )


@router.post(
    "/code-documents", response_model=CodeDocumentResponse, status_code=status.HTTP_201_CREATED
)
async def upload_code_document(
    # FastAPI's documented Form/File-as-default idiom (not real mutable-default risk).
    file: UploadFile = File(...),  # noqa: B008
    title: str = Form(...),
    source_type: CodeDocumentSourceType = Form(...),  # noqa: B008
    jurisdiction: str = Form(...),
    version: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> CodeDocumentResponse:
    """Upload a code document (.txt or .pdf) for chunking + embedding ingestion.

    Admin-only (PRP: "/code-library ... (admin)") -- this corpus is cited as
    authoritative by every user's compliance checks and Code-RAG answers, so
    only admins may add to or remove from it.
    """
    settings = get_settings()
    content = await file.read()
    if len(content) > settings.CODE_RAG_MAX_UPLOAD_BYTES:
        raise ValidationError(
            f"File exceeds the {settings.CODE_RAG_MAX_UPLOAD_BYTES // (1024 * 1024)}MB upload limit"
        )
    document = await rag_service.ingest_document(
        db,
        uploader=current_user,
        title=title,
        source_type=source_type,
        jurisdiction=jurisdiction,
        version=version,
        filename=file.filename or "upload.txt",
        content=content,
    )
    return _to_document_response(db, document)


@router.get("/code-documents", response_model=list[CodeDocumentResponse])
async def list_code_documents(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_admin_user),
) -> list[CodeDocumentResponse]:
    """List all ingested code documents. Admin-only (corpus management, not Q&A search)."""
    documents = rag_service.list_documents(db)
    return [_to_document_response(db, doc) for doc in documents]


@router.delete("/code-documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_code_document(
    document_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_admin_user),
) -> None:
    """Delete a code document and cascade-delete its chunks. Admin-only."""
    rag_service.delete_document(db, document_id)


@router.post("/code-rag/query", response_model=CodeRagQueryResponse)
async def query_code_rag(
    data: CodeRagQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CodeRagQueryResponse:
    """Ask a code-compliance question and get a cited answer grounded in ingested code."""
    return await rag_service.answer_query(db, user=current_user, query=data.query, top_k=data.top_k)

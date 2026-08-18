"""Admin Panel + Analytics module endpoints.

All routes are gated on `get_current_admin_user` (requires `User.is_admin`).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin_user
from app.models.code_chunk import CodeChunk
from app.models.user import User
from app.schemas.admin import AdminStatsResponse, AdminUserUpdateRequest
from app.schemas.auth import UserResponse
from app.schemas.code_rag import CodeDocumentResponse
from app.services import admin_service, rag_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: Session = Depends(get_db), _admin: User = Depends(get_current_admin_user)
) -> list[UserResponse]:
    """List all registered users."""
    return admin_service.list_users(db)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: AdminUserUpdateRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
) -> UserResponse:
    """Update a user's status (active/admin/verified)."""
    return admin_service.update_user(db, user_id, data)


@router.get("/stats", response_model=AdminStatsResponse)
async def get_stats(
    db: Session = Depends(get_db), _admin: User = Depends(get_current_admin_user)
) -> AdminStatsResponse:
    """Platform statistics: queries/day, generation success/rejection rate, most-cited sections."""
    return admin_service.compute_stats(db)


@router.get("/code-documents", response_model=list[CodeDocumentResponse])
async def list_code_documents(
    db: Session = Depends(get_db), _admin: User = Depends(get_current_admin_user)
) -> list[CodeDocumentResponse]:
    """List ingested code documents for administration."""
    documents = rag_service.list_documents(db)
    responses = []
    for document in documents:
        chunk_count = db.query(CodeChunk).filter(CodeChunk.document_id == document.id).count()
        responses.append(
            CodeDocumentResponse.model_validate(document, from_attributes=True).model_copy(
                update={"chunk_count": chunk_count}
            )
        )
    return responses

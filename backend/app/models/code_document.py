"""CodeDocument model — an ingested TNCDBR / municipal amendment source document."""
from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin

if TYPE_CHECKING:
    from app.models.code_chunk import CodeChunk
    from app.models.user import User


class CodeDocumentSourceType(str, enum.Enum):
    """Where a code document originates from."""

    tncdbr = "tncdbr"
    municipal_amendment = "municipal_amendment"


class CodeDocument(Base, CreatedAtMixin):
    """A source document (TNCDBR or a municipal amendment) ingested for RAG search."""

    __tablename__ = "code_documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[CodeDocumentSourceType] = mapped_column(
        Enum(CodeDocumentSourceType, name="code_document_source_type"), nullable=False
    )
    jurisdiction: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)

    uploaded_by_user: Mapped[User] = relationship(
        back_populates="uploaded_code_documents"
    )
    chunks: Mapped[list[CodeChunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

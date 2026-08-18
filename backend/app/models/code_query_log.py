"""CodeQueryLog model — an audit record of a Code-RAG question and cited answer."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin

if TYPE_CHECKING:
    from app.models.user import User


class CodeQueryLog(Base, CreatedAtMixin):
    """A logged Code-RAG query, its generated answer, and cited chunk ids."""

    __tablename__ = "code_query_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    cited_chunks: Mapped[list[int]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    user: Mapped[User] = relationship(back_populates="code_query_logs")

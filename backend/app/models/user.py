"""User model."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin

if TYPE_CHECKING:
    from app.models.chat import ChatSession
    from app.models.code_document import CodeDocument
    from app.models.code_query_log import CodeQueryLog
    from app.models.model_query_log import ModelQueryLog
    from app.models.refresh_token import RefreshToken


class User(Base, CreatedAtMixin):
    """A registered REVVY user (architect / BIM designer)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    chat_sessions: Mapped[list[ChatSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    uploaded_code_documents: Mapped[list[CodeDocument]] = relationship(
        back_populates="uploaded_by_user"
    )
    code_query_logs: Mapped[list[CodeQueryLog]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    model_query_logs: Mapped[list[ModelQueryLog]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"<User id={self.id} email={self.email!r}>"

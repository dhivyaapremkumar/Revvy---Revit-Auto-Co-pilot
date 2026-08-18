"""SQLAlchemy models for REVVY.

Import every model here so that importing `app.models` (as Alembic's
`env.py` does) registers all tables against `Base.metadata` for
autogenerate support.
"""
from app.models.base import Base, CreatedAtMixin, TimestampMixin
from app.models.chat import ChatMessage, ChatMessageRole, ChatSession
from app.models.code_chunk import CodeChunk
from app.models.code_document import CodeDocument, CodeDocumentSourceType
from app.models.code_query_log import CodeQueryLog
from app.models.model_query_log import ModelQueryLog
from app.models.refresh_token import RefreshToken
from app.models.user import User

__all__ = [
    "Base",
    "ChatMessage",
    "ChatMessageRole",
    "ChatSession",
    "CodeChunk",
    "CodeDocument",
    "CodeDocumentSourceType",
    "CodeQueryLog",
    "CreatedAtMixin",
    "ModelQueryLog",
    "RefreshToken",
    "TimestampMixin",
    "User",
]

"""Pydantic schemas for the Chat Copilot module."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.chat import ChatMessageRole


class ChatSessionCreate(BaseModel):
    """Payload for `POST /api/v1/chat/sessions`."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    revit_project_name: str | None = Field(default=None, max_length=255)


class ChatMessageResponse(BaseModel):
    """A single persisted chat message."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    role: ChatMessageRole
    content: str
    created_at: datetime


class ChatSessionResponse(BaseModel):
    """A chat session without its messages (list view)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    revit_project_name: str | None
    created_at: datetime
    updated_at: datetime


class ChatSessionDetailResponse(ChatSessionResponse):
    """A chat session including its full message history (detail view)."""

    messages: list[ChatMessageResponse] = Field(default_factory=list)


class ChatMessageCreate(BaseModel):
    """Payload for `POST /api/v1/chat/sessions/{id}/messages`."""

    content: str = Field(min_length=1)


class ChatMessageLogCreate(BaseModel):
    """Payload for `POST /api/v1/chat/sessions/{id}/messages/log`.

    For callers (the voice agent) that already generated both sides of a
    turn themselves and just need it recorded -- unlike `ChatMessageCreate`,
    this does NOT trigger a second, independent LLM reply.
    """

    role: ChatMessageRole
    content: str = Field(min_length=1)

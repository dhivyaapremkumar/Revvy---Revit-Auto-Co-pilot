"""Chat Copilot module endpoints. All scoped to `get_current_user`."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageLogCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionDetailResponse,
    ChatSessionResponse,
)
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[ChatSessionResponse]:
    """List the current user's chat sessions."""
    return chat_service.list_sessions(db, current_user)


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSessionResponse:
    """Create a new chat session."""
    return chat_service.create_session(db, current_user, data)


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
async def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSessionDetailResponse:
    """Get a chat session with its full message history."""
    return chat_service.get_session(db, current_user, session_id)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a chat session."""
    chat_service.delete_session(db, current_user, session_id)


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_message(
    session_id: int,
    data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatMessageResponse:
    """Send a message and get the AI's reply (persists both)."""
    return await chat_service.post_message(db, current_user, session_id, data.content)


@router.post(
    "/sessions/{session_id}/messages/log",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def log_message(
    session_id: int,
    data: ChatMessageLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatMessageResponse:
    """Record one side of an exchange the caller already generated itself
    (the voice agent's own transcript + spoken reply) -- unlike POST
    /messages, this never triggers a second LLM completion."""
    return chat_service.log_message(db, current_user, session_id, data.role, data.content)

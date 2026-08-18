"""Business logic for the Chat Copilot module.

Per CLAUDE.md's Chat Copilot module rule, chat responses that reference
building code must delegate to Code-RAG rather than answering from the
LLM's own knowledge. `_looks_like_code_question` is a lightweight keyword
heuristic that routes such messages through `rag_service.answer_query`
(cited, grounded-only-in-ingested-code) instead of a freeform completion.
Everything else falls back to a normal chat completion using recent
session history as context.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models.chat import ChatMessage, ChatMessageRole, ChatSession
from app.models.user import User
from app.schemas.chat import ChatSessionCreate
from app.services import llm_service, rag_service

logger = logging.getLogger(__name__)

# History window sent to the LLM as context for freeform completions.
_HISTORY_WINDOW = 20

_CODE_KEYWORDS = (
    "tncdbr",
    "building code",
    "building rule",
    "compliance",
    "setback",
    "fsi",
    "far ",
    "floor area ratio",
    "plot size",
    "plot area",
    "road width",
    "clause",
    "section ",
    "egress",
    "fire safety",
    "means of escape",
    "parking requirement",
    "height restriction",
    "code requires",
    "is it legal",
    "permissible",
)

_CHAT_SYSTEM_PROMPT = (
    "You are REVVY, an AI copilot embedded in Autodesk Revit for architects "
    "and BIM designers. Help with Revit workflow questions, modeling advice, "
    "and general assistance. You do NOT have building-code knowledge yourself — "
    "if the user asks about Tamil Nadu building code compliance, defer to the "
    "Code-RAG search rather than guessing."
)


def _looks_like_code_question(content: str) -> bool:
    lowered = content.lower()
    return any(keyword in lowered for keyword in _CODE_KEYWORDS)


def _continues_code_conversation(recent_history: list[ChatMessage]) -> bool:
    """True if a recent turn was code-related -- so a short clarifying reply
    ("residential, 3 floors") that matches no keyword on its own still
    routes back through Code-RAG instead of falling through to a plain,
    ungrounded chat completion that can't see the building code at all."""
    return any(_looks_like_code_question(msg.content) for msg in recent_history)


def create_session(db: Session, user: User, data: ChatSessionCreate) -> ChatSession:
    """Create a new chat session for `user`."""
    title = data.title or f"Chat {datetime.now(UTC):%b %d, %H:%M}"
    session = ChatSession(user_id=user.id, title=title, revit_project_name=data.revit_project_name)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_sessions(db: Session, user: User) -> list[ChatSession]:
    """List all chat sessions belonging to `user`, most recently updated first."""
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )


def get_session(db: Session, user: User, session_id: int) -> ChatSession:
    """Fetch a chat session owned by `user`. Raises `NotFoundError` otherwise."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if session is None:
        raise NotFoundError("Chat session")
    return session


def delete_session(db: Session, user: User, session_id: int) -> None:
    """Delete a chat session (and cascade its messages) owned by `user`."""
    session = get_session(db, user, session_id)
    db.delete(session)
    db.commit()


async def post_message(db: Session, user: User, session_id: int, content: str) -> ChatMessage:
    """Persist the user's message, generate an assistant reply, persist + return it."""
    session = get_session(db, user, session_id)

    # Fetched before adding this turn, so it's cleanly "everything prior".
    prior_messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(_HISTORY_WINDOW)
        .all()
    )
    prior_messages.reverse()

    user_message = ChatMessage(session_id=session.id, role=ChatMessageRole.user, content=content)
    db.add(user_message)
    db.commit()

    # A clarifying reply ("residential, 3 floors") often matches no code
    # keyword on its own -- if a recent turn was code-related, treat this
    # one as a continuation rather than falling through to plain chat,
    # which has no building-code grounding at all.
    if _looks_like_code_question(content) or _continues_code_conversation(prior_messages[-4:]):
        history = [{"role": msg.role.value, "content": msg.content} for msg in prior_messages[-8:]]
        rag_response = await rag_service.answer_query(db, user=user, query=content, history=history)
        assistant_content = rag_response.answer
    else:
        messages = (
            [{"role": "system", "content": _CHAT_SYSTEM_PROMPT}]
            + [{"role": msg.role.value, "content": msg.content} for msg in prior_messages]
            + [{"role": "user", "content": content}]
        )
        assistant_content = await llm_service.chat_completion(messages)

    assistant_message = ChatMessage(
        session_id=session.id, role=ChatMessageRole.assistant, content=assistant_content
    )
    db.add(assistant_message)
    # Bump `updated_at` explicitly so session lists can sort by recent activity
    # (the row otherwise wouldn't be touched by adding rows to a related table).
    session.updated_at = datetime.now(UTC)
    db.add(session)
    db.commit()
    db.refresh(assistant_message)
    return assistant_message


def log_message(
    db: Session, user: User, session_id: int, role: ChatMessageRole, content: str
) -> ChatMessage:
    """Record one side of an already-generated exchange (the voice agent's own
    transcript + reply) without triggering another LLM completion."""
    session = get_session(db, user, session_id)

    message = ChatMessage(session_id=session.id, role=role, content=content)
    db.add(message)
    session.updated_at = datetime.now(UTC)
    db.add(session)
    db.commit()
    db.refresh(message)
    return message

"""Business logic for the Model Query module (read-only Revit queries).

The add-in supplies a snapshot of the currently open document; this
service only reasons over that snapshot via the LLM and logs the query —
it never issues any instruction back to the add-in, satisfying "Read
queries never mutate the Revit model" (CLAUDE.md).
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.model_query_log import ModelQueryLog
from app.models.user import User
from app.services import llm_service

logger = logging.getLogger(__name__)

_MODEL_QUERY_SYSTEM_PROMPT = (
    "You are REVVY's read-only Revit model query assistant. You will be given "
    "a JSON snapshot of the currently open Revit document (elements, "
    "categories, parameters) and a natural-language question about it. "
    "Answer using ONLY the data provided in the snapshot — if the snapshot "
    "doesn't contain enough information to answer, say so explicitly. "
    "Never suggest or imply that the model has been or should be modified; "
    "this is a read-only query."
)


async def run_model_query(
    db: Session,
    *,
    user: User,
    revit_project_name: str,
    query: str,
    model_state: dict[str, Any],
) -> tuple[str, dict[str, Any] | None]:
    """Answer a read-only question about `model_state` and log it."""
    messages = [
        {"role": "system", "content": _MODEL_QUERY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Model snapshot:\n{json.dumps(model_state, default=str)}\n\nQuestion: {query}",
        },
    ]
    result_summary = await llm_service.chat_completion(messages)

    db.add(
        ModelQueryLog(
            user_id=user.id,
            revit_project_name=revit_project_name,
            query=query,
            result_summary=result_summary,
        )
    )
    db.commit()

    return result_summary, model_state or None

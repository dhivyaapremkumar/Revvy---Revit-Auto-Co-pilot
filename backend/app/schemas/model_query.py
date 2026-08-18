"""Pydantic schemas for the Model Query module."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ModelQueryRequest(BaseModel):
    """Payload for `POST /api/v1/model/query`.

    The pyRevit add-in reads the currently open document and posts a
    snapshot of it (`model_state`) alongside the natural-language
    `query` — the backend never reaches out to Revit itself, it only
    reasons over what the add-in already read (read-only by construction).
    """

    revit_project_name: str = Field(min_length=1, max_length=255)
    query: str = Field(min_length=1)
    model_state: dict[str, Any] = Field(
        default_factory=dict,
        description="Snapshot of the currently open document from the pyRevit add-in.",
    )


class ModelQueryResponse(BaseModel):
    """Response for `POST /api/v1/model/query`."""

    result_summary: str
    raw_data: dict[str, Any] | None = None

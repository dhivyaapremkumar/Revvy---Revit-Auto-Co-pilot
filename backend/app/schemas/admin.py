"""Pydantic schemas for the Admin Panel + Analytics module."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class AdminUserUpdateRequest(BaseModel):
    """Payload for `PUT /api/v1/admin/users/{id}` — admin-controlled fields only."""

    is_active: bool | None = None
    is_admin: bool | None = None
    is_verified: bool | None = None


class DailyCount(BaseModel):
    """One point in a queries-per-day time series."""

    date: date
    count: int


class CitedSectionCount(BaseModel):
    """How often a given code section has been cited in Code-RAG answers."""

    section_reference: str
    document_title: str
    count: int


class AdminStatsResponse(BaseModel):
    """Response for `GET /api/v1/admin/stats` — real aggregate queries, not fake numbers."""

    total_users: int
    active_users: int
    code_queries_per_day: list[DailyCount]
    model_queries_per_day: list[DailyCount]
    code_queries_total: int
    model_queries_total: int
    most_cited_sections: list[CitedSectionCount]

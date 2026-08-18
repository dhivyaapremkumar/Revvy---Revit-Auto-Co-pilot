"""Business logic for the Admin Panel + Analytics module.

`compute_stats` runs real aggregate queries against the logged tables
(no fabricated numbers) — queries/day over the last 30 days and
most-cited code sections.
"""
from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.exceptions import NotFoundError
from app.models.code_chunk import CodeChunk
from app.models.code_query_log import CodeQueryLog
from app.models.model_query_log import ModelQueryLog
from app.models.user import User
from app.schemas.admin import (
    AdminStatsResponse,
    AdminUserUpdateRequest,
    CitedSectionCount,
    DailyCount,
)

_STATS_WINDOW_DAYS = 30
_TOP_CITED_SECTIONS = 10


def list_users(db: Session) -> list[User]:
    """List all registered users, most recently created first."""
    return db.query(User).order_by(User.created_at.desc()).all()


def update_user(db: Session, user_id: int, data: AdminUserUpdateRequest) -> User:
    """Update an arbitrary user's admin-controlled fields (active/admin/verified)."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise NotFoundError("User")

    if data.is_active is not None:
        user.is_active = data.is_active
    if data.is_admin is not None:
        user.is_admin = data.is_admin
    if data.is_verified is not None:
        user.is_verified = data.is_verified

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _daily_counts(db: Session, model, since: datetime) -> list[DailyCount]:
    rows = (
        db.query(func.date(model.created_at).label("day"), func.count().label("count"))
        .filter(model.created_at >= since)
        .group_by(func.date(model.created_at))
        .order_by(func.date(model.created_at))
        .all()
    )
    return [DailyCount(date=row.day if isinstance(row.day, date) else row.day.date(), count=row.count) for row in rows]


def _most_cited_sections(db: Session) -> list[CitedSectionCount]:
    cited_chunk_lists = db.query(CodeQueryLog.cited_chunks).all()
    chunk_id_counts: Counter[int] = Counter()
    for (cited_chunks,) in cited_chunk_lists:
        chunk_id_counts.update(cited_chunks or [])

    if not chunk_id_counts:
        return []

    chunks = (
        db.query(CodeChunk)
        .options(joinedload(CodeChunk.document))
        .filter(CodeChunk.id.in_(chunk_id_counts.keys()))
        .all()
    )
    section_counts: Counter[tuple[str, str]] = Counter()
    for chunk in chunks:
        key = (chunk.section_reference, chunk.document.title)
        section_counts[key] += chunk_id_counts[chunk.id]

    top = section_counts.most_common(_TOP_CITED_SECTIONS)
    return [
        CitedSectionCount(section_reference=section, document_title=title, count=count)
        for (section, title), count in top
    ]


def compute_stats(db: Session) -> AdminStatsResponse:
    """Compute platform statistics from real aggregate queries."""
    since = datetime.now(UTC) - timedelta(days=_STATS_WINDOW_DAYS)

    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0

    code_queries_total = db.query(func.count(CodeQueryLog.id)).scalar() or 0
    model_queries_total = db.query(func.count(ModelQueryLog.id)).scalar() or 0

    return AdminStatsResponse(
        total_users=total_users,
        active_users=active_users,
        code_queries_per_day=_daily_counts(db, CodeQueryLog, since),
        model_queries_per_day=_daily_counts(db, ModelQueryLog, since),
        code_queries_total=code_queries_total,
        model_queries_total=model_queries_total,
        most_cited_sections=_most_cited_sections(db),
    )

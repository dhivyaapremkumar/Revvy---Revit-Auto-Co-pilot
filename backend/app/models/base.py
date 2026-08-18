"""Declarative base and shared mixins for all REVVY database models.

Every model in `app/models/` should inherit from `Base` (and, where the
PRP calls for timestamp columns, from `TimestampMixin` or `CreatedAtMixin`)
so Alembic's autogenerate can discover the full schema via
`Base.metadata`.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base class for all ORM models."""


class TimestampMixin:
    """Adds `created_at` and `updated_at` columns to a model.

    Use for models where the PRP explicitly lists both timestamps
    (e.g. `ChatSession`).
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CreatedAtMixin:
    """Adds a single `created_at` column to a model.

    Use for append-only / log-style models where the PRP only lists
    `created_at` (no `updated_at`).
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

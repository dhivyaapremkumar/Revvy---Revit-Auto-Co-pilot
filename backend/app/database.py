"""Database engine, session factory, and FastAPI dependency for REVVY.

`DATABASE_URL` is sourced from `app.config.settings` (env vars / `.env`),
never hardcoded, per CLAUDE.md.
"""
from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a `Session` and always closes it.

    Usage:
        @router.get("/users/{id}")
        async def get_user(id: int, db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

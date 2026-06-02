from __future__ import annotations

from typing import Any

from sqlalchemy.exc import SQLAlchemyError


def commit_or_rollback(session: Any) -> None:
    """Commit SQLAlchemy work and rollback only on SQLAlchemy failures."""
    try:
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise


def commit_refresh_or_rollback(session: Any, orm_obj: Any) -> None:
    commit_or_rollback(session)
    session.refresh(orm_obj)

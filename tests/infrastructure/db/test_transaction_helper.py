import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.infrastructure.db.sqlalchemy.repositories._transaction import (
    commit_or_rollback,
    commit_refresh_or_rollback,
)


class FailingSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    def commit(self) -> None:
        self.committed = True
        raise SQLAlchemyError("commit failed")

    def rollback(self) -> None:
        self.rolled_back = True


class SuccessfulSession:
    def __init__(self) -> None:
        self.committed = False
        self.refreshed = None

    def commit(self) -> None:
        self.committed = True

    def refresh(self, orm_obj) -> None:
        self.refreshed = orm_obj


def test_commit_or_rollback_rolls_back_sqlalchemy_failures():
    session = FailingSession()

    with pytest.raises(SQLAlchemyError):
        commit_or_rollback(session)

    assert session.committed is True
    assert session.rolled_back is True


def test_commit_refresh_or_rollback_refreshes_after_successful_commit():
    session = SuccessfulSession()
    orm_obj = object()

    commit_refresh_or_rollback(session, orm_obj)

    assert session.committed is True
    assert session.refreshed is orm_obj

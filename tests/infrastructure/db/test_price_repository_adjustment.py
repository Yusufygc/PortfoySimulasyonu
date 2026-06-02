from datetime import date
from decimal import Decimal

from src.infrastructure.db.sqlalchemy.repositories.sa_price_repository import SQLAlchemyPriceRepository


class FakeQuery:
    def __init__(self):
        self.filters = []
        self.updated_values = None
        self.synchronize_session = None

    def filter(self, condition):
        self.filters.append(condition)
        return self

    def update(self, values, synchronize_session=False):
        self.updated_values = values
        self.synchronize_session = synchronize_session
        return 2


class FakeSession:
    def __init__(self):
        self.query_arg = None
        self.query_obj = FakeQuery()
        self.committed = False
        self.rolled_back = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def query(self, arg):
        self.query_arg = arg
        return self.query_obj

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class FakeProvider:
    def __init__(self):
        self.session = FakeSession()

    def get_session(self):
        return self.session


def test_adjust_prices_before_date_updates_stock_history_only():
    provider = FakeProvider()
    repo = SQLAlchemyPriceRepository(provider)

    updated = repo.adjust_prices_before_date(
        stock_id=7,
        before_date=date(2026, 5, 5),
        factor=Decimal("0.1354392670"),
    )

    assert updated == 2
    assert len(provider.session.query_obj.filters) == 2
    assert provider.session.query_obj.updated_values
    assert provider.session.query_obj.synchronize_session is False
    assert provider.session.committed is True
    assert provider.session.rolled_back is False

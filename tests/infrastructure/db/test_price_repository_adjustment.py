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


def test_adjustment_scales_open_high_low_with_close(tmp_path):
    """Bölünme düzeltmesi yalnızca kapanışı değiştirirse OHLC tutarsızlaşır (mum gövdesi kapanışın 11 katı kalırdı)."""
    from src.domain.models.daily_price import DailyPrice
    from src.infrastructure.db.db_config import SQLiteConfig
    from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
    from src.infrastructure.db.sqlalchemy.orm_models import ORMStock

    provider = SQLAlchemyEngineProvider(SQLiteConfig(db_path=str(tmp_path / "ohlc.db")))
    with provider.get_session() as session:
        session.add(ORMStock(id=1, ticker="SDTTR"))
        session.commit()
    repo = SQLAlchemyPriceRepository(provider)
    repo.upsert_daily_prices_bulk([DailyPrice(
        id=None, stock_id=1, price_date=date(2026, 8, 20), close_price=Decimal("253"),
        open_price=Decimal("242"), high_price=Decimal("264"), low_price=Decimal("231"), volume=1000,
    )])

    assert repo.adjust_prices_before_date(1, date(2026, 8, 21), Decimal("1") / Decimal("11")) == 1

    stored = repo.get_price_for_date(1, date(2026, 8, 20))
    assert (stored.open_price, stored.high_price, stored.low_price, stored.close_price) == (
        Decimal("22"), Decimal("24"), Decimal("21"), Decimal("23"))
    assert stored.volume == 1000

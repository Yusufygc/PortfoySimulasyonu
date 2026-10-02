"""SQLite'ta latest_prices ve golden_cross_events upsert'leri (MySQL'e özgü SQL kullanılmamalı)."""
from datetime import date, datetime
from decimal import Decimal

import pytest

from src.domain.models.golden_cross_event import CrossType, GoldenCrossEvent
from src.domain.models.latest_price import LatestPrice
from src.infrastructure.db.db_config import SQLiteConfig
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMStock
from src.infrastructure.db.sqlalchemy.repositories.sa_golden_cross_repository import SQLAlchemyGoldenCrossRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_latest_price_repository import SQLAlchemyLatestPriceRepository


@pytest.fixture
def provider(tmp_path):
    provider = SQLAlchemyEngineProvider(SQLiteConfig(db_path=str(tmp_path / "test.db")))
    with provider.get_session() as session:
        for stock_id, ticker in ((1, "AAA.IS"), (2, "BBB.IS")):
            session.add(ORMStock(id=stock_id, ticker=ticker, name=ticker))
        session.commit()
    return provider


def _latest(stock_id, price, hour=10):
    now = datetime(2026, 10, 2, hour, 0)
    return LatestPrice(None, stock_id, Decimal(price), now, "intraday", "price_lookup", now)


def test_latest_price_upsert_inserts_then_updates(provider):
    repo = SQLAlchemyLatestPriceRepository(provider)

    repo.upsert_latest_prices([_latest(1, "10.5"), _latest(2, "20")])
    assert repo.get_latest_price_map([1, 2]) == {1: Decimal("10.5"), 2: Decimal("20")}
    first_ids = {sid: lp.id for sid, lp in repo.get_latest_prices([1, 2]).items()}

    repo.upsert_latest_prices([_latest(1, "11.25", hour=12)])
    updated = repo.get_latest_prices([1, 2])
    assert updated[1].price == Decimal("11.25") and updated[1].as_of.hour == 12
    assert updated[2].price == Decimal("20")
    assert {sid: lp.id for sid, lp in updated.items()} == first_ids  # satır kimliği korunur


def test_latest_price_upsert_empty_is_noop(provider):
    repo = SQLAlchemyLatestPriceRepository(provider)
    repo.upsert_latest_prices([])
    assert repo.get_latest_price_map([1]) == {}


def _event(stock_id, day, kind=CrossType.GOLDEN, close="100"):
    return GoldenCrossEvent(
        id=None, stock_id=stock_id, ticker="X", cross_date=day, cross_type=kind,
        short_ma=Decimal("1"), long_ma=Decimal("2"), close_price=Decimal(close),
    )


def test_golden_cross_bulk_insert_counts_only_new_events(provider):
    repo = SQLAlchemyGoldenCrossRepository(provider)
    events = [_event(1, date(2026, 3, 2)), _event(1, date(2026, 4, 2), CrossType.DEATH), _event(2, date(2026, 3, 2))]

    assert repo.upsert_events_bulk(events) == 3
    # aynı olaylar + bir yenisi: yalnızca yeni olan sayılır, mevcutlar korunur
    again = events + [_event(2, date(2026, 5, 4))]
    assert repo.upsert_events_bulk(again) == 1

    stored = repo.get_recent_events(since=date(2026, 1, 1), limit=50)
    assert len(stored) == 4
    assert {e.cross_type for e in stored} == {CrossType.GOLDEN, CrossType.DEATH}
    assert repo.upsert_events_bulk([]) == 0

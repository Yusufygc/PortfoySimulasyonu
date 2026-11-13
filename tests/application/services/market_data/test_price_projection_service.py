from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from src.application.services.market_data.price_projection_service import PriceProjectionService
from src.domain.models.daily_price import DailyPrice
from src.domain.models.market_bar import MarketBar
from src.infrastructure.db.db_config import SQLiteConfig
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMStock
from src.infrastructure.db.sqlalchemy.repositories.sa_price_repository import SQLAlchemyPriceRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_stock_repository import SQLAlchemyStockRepository

DAYS = [date(2026, 8, 17) + timedelta(days=i) for i in range(5)]  # Pzt-Cum


class FakeHistory:
    def __init__(self, bars_by_ticker):
        self._bars = bars_by_ticker

    def get_price_series(self, ticker, start, end, adjusted=True):
        return [b for b in self._bars.get(ticker, []) if start <= b.price_date <= end]

    def get_price_series_bulk(self, tickers, start, end, adjusted=True):
        return {t: self.get_price_series(t, start, end) for t in tickers if t in self._bars}

    def get_last_bars(self, ticker, count=2, adjusted=True):
        return list(reversed(self._bars.get(ticker, [])))[:count]


def _bar(ticker, day, close, volume=1000):
    return MarketBar(ticker=ticker, price_date=day, close_price=close, open_price=close - 0.5,
                     high_price=close + 1, low_price=close - 1, volume=volume)


@pytest.fixture
def repos(tmp_path):
    provider = SQLAlchemyEngineProvider(SQLiteConfig(db_path=str(tmp_path / "p.db")))
    with provider.get_session() as s:
        s.add_all([ORMStock(id=1, ticker="SDTTR"), ORMStock(id=2, ticker="OLD.IS")])
        s.commit()
    return SQLAlchemyPriceRepository(provider), SQLAlchemyStockRepository(provider)


def test_projection_copies_adjusted_bars_and_removes_stale_rows(repos):
    prices, stocks = repos
    prices.upsert_daily_prices_bulk([
        DailyPrice(None, 1, DAYS[0], D("253")),          # eski ham fiyat: DuckDB değeriyle değişir
        DailyPrice(None, 1, DAYS[2], D("23.9")),         # DuckDB'de bu gün yok (hayalet silinmiş): silinir
    ])
    history = FakeHistory({"SDTTR": [_bar("SDTTR", DAYS[0], 23.0), _bar("SDTTR", DAYS[1], 23.5),
                                     _bar("SDTTR", DAYS[2], 23.5, volume=0), _bar("SDTTR", DAYS[3], 24.0)]})

    result = PriceProjectionService(history, prices, stocks).project([1])

    stored = {p.price_date: p for p in prices.get_price_series(1, DAYS[0], DAYS[4])}
    assert sorted(stored) == [DAYS[0], DAYS[1], DAYS[3]]
    assert stored[DAYS[0]].close_price == D("23.0") and stored[DAYS[0]].open_price == D("22.5")
    assert stored[DAYS[0]].source == "duckdb" and stored[DAYS[0]].volume == 1000
    assert result.written == {1: 3} and result.deleted == {1: 1} and result.last_prices == {1: D("24.0")}


def test_stock_missing_in_duckdb_is_reported_and_untouched(repos):
    prices, stocks = repos
    prices.upsert_daily_prices_bulk([DailyPrice(None, 2, DAYS[0], D("5"))])

    result = PriceProjectionService(FakeHistory({}), prices, stocks).project()

    assert sorted(result.missing) == ["OLD", "SDTTR"]
    assert prices.get_price_for_date(2, DAYS[0]).close_price == D("5")


def test_ghost_filter_and_window(repos):
    prices, stocks = repos
    history = FakeHistory({"SDTTR": [_bar("SDTTR", d, 20.0 + i) for i, d in enumerate(DAYS)]})
    ghost_day = DAYS[1]
    service = PriceProjectionService(history, prices, stocks, ghost_filter=lambda bar: bar.price_date == ghost_day)

    service.project([1], start=DAYS[0], end=DAYS[2])

    assert [p.price_date for p in prices.get_price_series(1, DAYS[0], DAYS[4])] == [DAYS[0], DAYS[2]]


def test_second_projection_writes_nothing(repos):
    prices, stocks = repos
    history = FakeHistory({"SDTTR": [_bar("SDTTR", d, 20.0 + i) for i, d in enumerate(DAYS)]})
    service = PriceProjectionService(history, prices, stocks)
    assert service.project().written_count == 5
    again = service.project()
    assert again.written_count == 0 and again.deleted == {}

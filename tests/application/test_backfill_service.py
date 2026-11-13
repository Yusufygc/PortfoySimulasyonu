"""BackfillService: indirme MarketPriceRefresher üzerinden (DuckDB + SQLite yansıması), silme iki depoda."""
from datetime import date
from types import SimpleNamespace as NS

import pytest

from src.application.services.market_data.market_price_refresher import RefreshResult
from src.application.services.simulation.backfill_service import BackfillService

A, B = NS(id=1, ticker="AAA"), NS(id=2, ticker="BBB")


class FakeStocks:
    def __init__(self, stocks):
        self._stocks = stocks

    def get_all_stocks(self):
        return list(self._stocks)

    def get_stock_by_id(self, stock_id):
        return next((s for s in self._stocks if s.id == stock_id), None)


class FakeRefresher:
    def __init__(self, updated=None, errors=()):
        self.calls, self.deleted = [], []
        self._updated, self._errors = updated or {}, list(errors)

    def refresh(self, stocks, start, end):
        self.calls.append(([s.id for s in stocks], start, end))
        return RefreshResult(updated=dict(self._updated), errors=list(self._errors))

    def delete_range(self, stocks, start, end):
        self.deleted.append(([s.id for s in stocks], start, end))
        return 3


class FakePrices:
    def __init__(self):
        self.deletes = []

    def delete_prices_in_range(self, start, end, stock_ids=None):
        self.deletes.append((start, end, stock_ids))
        return 4


def _service(stocks=(A, B), refresher=None):
    refresher = refresher or FakeRefresher({1: 5, 2: 7})
    return BackfillService(FakeStocks(stocks), FakePrices(), refresher), refresher


def test_backfill_range_refreshes_all_stocks_and_returns_written_rows():
    service, refresher = _service()
    assert service.backfill_range(date(2026, 1, 1), date(2026, 1, 31)) == 12
    assert refresher.calls == [([1, 2], date(2026, 1, 1), date(2026, 1, 31))]


def test_backfill_range_validates_input():
    service, _ = _service()
    with pytest.raises(ValueError):
        service.backfill_range(date(2026, 2, 1), date(2026, 1, 1))
    with pytest.raises(ValueError, match="kayıtlı hisse yok"):
        _service(stocks=())[0].backfill_range(date(2026, 1, 1), date(2026, 1, 2))


def test_backfill_for_single_stock_refreshes_only_that_stock():
    service, refresher = _service(refresher=FakeRefresher({2: 9}))
    assert service.backfill_for_single_stock(2, "BBB", date(2026, 1, 1), date(2026, 1, 2)) == 9
    assert refresher.calls == [([2], date(2026, 1, 1), date(2026, 1, 2))]
    with pytest.raises(ValueError):
        service.backfill_for_single_stock(99, "YOK", date(2026, 1, 1), date(2026, 1, 2))


def test_delete_range_removes_from_duckdb_and_sqlite():
    service, refresher = _service()
    assert service.delete_range(date(2026, 1, 1), date(2026, 1, 31)) == 4
    assert refresher.deleted == [([1, 2], date(2026, 1, 1), date(2026, 1, 31))]
    with pytest.raises(ValueError):
        service.delete_range(date(2026, 2, 1), date(2026, 1, 1))

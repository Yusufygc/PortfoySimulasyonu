from datetime import date
from decimal import Decimal as D
from types import SimpleNamespace as NS

from src.application.services.market_data.market_price_refresher import MarketPriceRefresher
from src.application.services.market_data.price_projection_service import ProjectionResult


class FakeDownloader:
    def __init__(self, bars, errors=()):
        self.bars, self.errors, self.calls = bars, list(errors), []

    def download_daily(self, tickers, start, end_exclusive):
        self.calls.append((list(tickers), start, end_exclusive))
        return self.bars, len(tickers), self.errors


class FakeStore:
    def __init__(self):
        self.written, self.deleted = [], []

    def write_bars(self, bars):
        self.written.extend(bars)

    def delete_range(self, tickers, start, end):
        self.deleted.append((list(tickers), start, end))
        return 2


class FakeProjection:
    def __init__(self):
        self.calls = []

    def project(self, stock_ids=None, start=None, end=None):
        self.calls.append((list(stock_ids), start, end))
        return ProjectionResult(written={1: 3}, last_prices={1: D("10")})


def test_refresh_downloads_into_duckdb_then_projects_same_window():
    downloader, store, projection = FakeDownloader([NS(ticker="ASELS")], errors=["x"]), FakeStore(), FakeProjection()
    refresher = MarketPriceRefresher(downloader, store, projection)

    result = refresher.refresh([NS(id=1, ticker="ASELS.IS")], date(2026, 1, 5), date(2026, 1, 9))

    assert downloader.calls == [(["ASELS"], date(2026, 1, 5), date(2026, 1, 10))]  # bitiş dahil -> exclusive +1
    assert len(store.written) == 1 and result.downloaded_bars == 1
    assert projection.calls == [([1], date(2026, 1, 5), date(2026, 1, 9))]
    assert (result.updated_count, result.last_prices, result.errors) == (3, {1: D("10")}, ["x"])


def test_refresh_without_downloader_still_projects_existing_duckdb_data():
    projection = FakeProjection()
    result = MarketPriceRefresher(None, FakeStore(), projection).refresh([NS(id=1, ticker="A")], date(2026, 1, 5), date(2026, 1, 5))
    assert projection.calls and result.errors == ["Piyasa verisi indiricisi yok."]


def test_delete_range_cleans_tickers():
    store = FakeStore()
    MarketPriceRefresher(None, store, FakeProjection()).delete_range([NS(id=1, ticker="asels.is")], date(2026, 1, 1), date(2026, 1, 2))
    assert store.deleted == [(["ASELS"], date(2026, 1, 1), date(2026, 1, 2))]

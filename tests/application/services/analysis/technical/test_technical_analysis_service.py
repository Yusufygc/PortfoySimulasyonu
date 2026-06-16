"""TechnicalAnalysisService mock testleri."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from src.application.services.analysis.technical.technical_analysis_service import (
    ScanResult,
    TechnicalAnalysisService,
)
from src.domain.models.daily_price import DailyPrice
from src.domain.models.golden_cross_event import CrossType
from src.domain.models.stock import Stock


def _stock(id_: int, ticker: str) -> Stock:
    return Stock(id=id_, ticker=ticker, name=ticker, currency_code="TRY")


def _series_with_cross(stock_id: int) -> list[DailyPrice]:
    """flat + rising → SMA20/SMA50 golden cross üretir."""
    start = date(2020, 1, 1)
    flat = [100.0] * 100
    rising = [100.0 + i for i in range(1, 121)]
    values = flat + rising
    return [
        DailyPrice(
            id=None,
            stock_id=stock_id,
            price_date=start + timedelta(days=i),
            close_price=Decimal(str(v)),
        )
        for i, v in enumerate(values)
    ]


class TestScanAll:
    def test_scan_all_inserts_cross_events(self):
        stock = _stock(1, "FROTO")
        price_repo = MagicMock()
        price_repo.get_price_series.return_value = _series_with_cross(1)
        stock_repo = MagicMock()
        stock_repo.get_all_stocks.return_value = [stock]
        cross_repo = MagicMock()
        cross_repo.upsert_events_bulk.return_value = 2

        svc = TechnicalAnalysisService(
            price_repo=price_repo,
            stock_repo=stock_repo,
            golden_cross_repo=cross_repo,
            short_period=20, long_period=50,
        )
        res = svc.scan_all(today=date(2020, 12, 31))

        assert isinstance(res, ScanResult)
        assert res.scanned_count == 1
        assert res.skipped_count == 0
        cross_repo.upsert_events_bulk.assert_called_once()

    def test_scan_all_skips_insufficient_data(self):
        stock = _stock(1, "X")
        price_repo = MagicMock()
        price_repo.get_price_series.return_value = []  # boş
        stock_repo = MagicMock()
        stock_repo.get_all_stocks.return_value = [stock]
        cross_repo = MagicMock()
        cross_repo.upsert_events_bulk.return_value = 0

        svc = TechnicalAnalysisService(
            price_repo=price_repo, stock_repo=stock_repo, golden_cross_repo=cross_repo,
            short_period=20, long_period=50,
        )
        res = svc.scan_all(today=date(2025, 1, 1))

        assert res.scanned_count == 1
        assert res.skipped_count == 1
        cross_repo.upsert_events_bulk.assert_not_called()

    def test_scan_all_empty_stock_list(self):
        price_repo = MagicMock()
        stock_repo = MagicMock()
        stock_repo.get_all_stocks.return_value = []
        cross_repo = MagicMock()

        svc = TechnicalAnalysisService(
            price_repo=price_repo, stock_repo=stock_repo, golden_cross_repo=cross_repo,
        )
        res = svc.scan_all()

        assert res.scanned_count == 0
        assert res.new_event_count == 0


class TestScanTicker:
    def test_scan_ticker_missing_stock(self):
        price_repo = MagicMock()
        stock_repo = MagicMock()
        stock_repo.get_stock_by_ticker.return_value = None
        cross_repo = MagicMock()
        svc = TechnicalAnalysisService(price_repo, stock_repo, cross_repo)
        res = svc.scan_ticker("XYZW")
        assert res.scanned_count == 0
        cross_repo.upsert_events_bulk.assert_not_called()

    def test_scan_ticker_calls_repo(self):
        stock = _stock(7, "FROTO")
        stock_repo = MagicMock()
        stock_repo.get_stock_by_ticker.return_value = stock
        price_repo = MagicMock()
        price_repo.get_price_series.return_value = _series_with_cross(7)
        cross_repo = MagicMock()
        cross_repo.upsert_events_bulk.return_value = 3
        svc = TechnicalAnalysisService(
            price_repo, stock_repo, cross_repo,
            short_period=20, long_period=50,
        )
        res = svc.scan_ticker("froto", today=date(2020, 12, 31))
        assert res.new_event_count == 3
        cross_repo.upsert_events_bulk.assert_called_once()


class TestQueries:
    def test_get_recent_events_delegates_to_repo(self):
        price_repo = MagicMock()
        stock_repo = MagicMock()
        cross_repo = MagicMock()
        cross_repo.get_recent_events.return_value = []
        svc = TechnicalAnalysisService(price_repo, stock_repo, cross_repo)
        svc.get_recent_events(days=10, cross_type=CrossType.GOLDEN, limit=50)
        cross_repo.get_recent_events.assert_called_once()
        args, kwargs = cross_repo.get_recent_events.call_args
        assert kwargs["cross_type"] == CrossType.GOLDEN
        assert kwargs["limit"] == 50

    def test_get_events_for_ticker_missing(self):
        price_repo = MagicMock()
        stock_repo = MagicMock()
        stock_repo.get_stock_by_ticker.return_value = None
        cross_repo = MagicMock()
        svc = TechnicalAnalysisService(price_repo, stock_repo, cross_repo)
        assert svc.get_events_for_ticker("UNK") == []

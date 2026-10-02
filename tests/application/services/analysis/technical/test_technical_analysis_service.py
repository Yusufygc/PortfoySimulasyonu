"""TechnicalAnalysisService mock testleri (DuckDB piyasa geçmişi üzerinden, ticker anahtarlı)."""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock

from src.application.services.analysis.technical import technical_analysis_service as svc_module
from src.application.services.analysis.technical.technical_analysis_service import (
    ScanResult,
    TechnicalAnalysisService,
)
from src.domain.models.golden_cross_event import CrossType
from src.domain.models.market_bar import MarketBar


def _series_with_cross(ticker: str) -> list[MarketBar]:
    """flat + rising → SMA20/SMA50 golden cross üretir."""
    start = date(2020, 1, 1)
    flat = [100.0] * 100
    rising = [100.0 + i for i in range(1, 121)]
    return [
        MarketBar(ticker=ticker, price_date=start + timedelta(days=i), close_price=v)
        for i, v in enumerate(flat + rising)
    ]


def _history(series: dict) -> MagicMock:
    history = MagicMock()
    history.list_tickers.return_value = list(series)
    history.has_ticker.side_effect = lambda t: t in series
    history.get_price_series_bulk.side_effect = lambda tickers, start, end: {t: series[t] for t in tickers if t in series}
    history.get_price_series.side_effect = lambda ticker, start, end: series.get(ticker, [])
    return history


class TestScanAll:
    def test_scan_all_inserts_cross_events_with_plain_ticker(self):
        cross_repo = MagicMock()
        cross_repo.upsert_events_bulk.return_value = 2

        svc = TechnicalAnalysisService(
            market_history_repo=_history({"FROTO": _series_with_cross("FROTO")}),
            golden_cross_repo=cross_repo,
            short_period=20, long_period=50,
        )
        res = svc.scan_all(today=date(2020, 12, 31))

        assert isinstance(res, ScanResult)
        assert res.scanned_count == 1
        assert res.skipped_count == 0
        cross_repo.upsert_events_bulk.assert_called_once()
        events = cross_repo.upsert_events_bulk.call_args.args[0]
        assert events and all(e.ticker == "FROTO" for e in events)

    def test_scan_all_skips_insufficient_data(self):
        cross_repo = MagicMock()
        svc = TechnicalAnalysisService(
            market_history_repo=_history({"X": []}), golden_cross_repo=cross_repo, short_period=20, long_period=50,
        )

        res = svc.scan_all(today=date(2025, 1, 1))

        assert res.scanned_count == 1
        assert res.skipped_count == 1
        cross_repo.upsert_events_bulk.assert_not_called()

    def test_scan_all_empty_catalog(self):
        svc = TechnicalAnalysisService(market_history_repo=_history({}), golden_cross_repo=MagicMock())

        res = svc.scan_all()

        assert res.scanned_count == 0
        assert res.new_event_count == 0

    def test_scan_all_reads_catalog_in_chunks(self, monkeypatch):
        monkeypatch.setattr(svc_module, "_SCAN_CHUNK", 2)
        history = _history({f"T{i}": [] for i in range(5)})
        svc = TechnicalAnalysisService(market_history_repo=history, golden_cross_repo=MagicMock())

        res = svc.scan_all()

        assert res.scanned_count == 5 and res.skipped_count == 5
        assert history.get_price_series_bulk.call_count == 3


class TestScanTicker:
    def test_scan_ticker_unknown_ticker(self):
        cross_repo = MagicMock()
        svc = TechnicalAnalysisService(_history({}), cross_repo)

        res = svc.scan_ticker("XYZW")

        assert res.scanned_count == 0
        cross_repo.upsert_events_bulk.assert_not_called()

    def test_scan_ticker_calls_repo(self):
        cross_repo = MagicMock()
        cross_repo.upsert_events_bulk.return_value = 3
        svc = TechnicalAnalysisService(
            _history({"FROTO": _series_with_cross("FROTO")}), cross_repo, short_period=20, long_period=50,
        )

        res = svc.scan_ticker("froto.is", today=date(2020, 12, 31))

        assert res.new_event_count == 3
        cross_repo.upsert_events_bulk.assert_called_once()


class TestQueries:
    def test_get_recent_events_delegates_to_repo(self):
        cross_repo = MagicMock()
        cross_repo.get_recent_events.return_value = []
        svc = TechnicalAnalysisService(_history({}), cross_repo)
        svc.get_recent_events(days=10, cross_type=CrossType.GOLDEN, limit=50)
        cross_repo.get_recent_events.assert_called_once()
        args, kwargs = cross_repo.get_recent_events.call_args
        assert kwargs["cross_type"] == CrossType.GOLDEN
        assert kwargs["limit"] == 50

    def test_get_events_for_ticker_strips_suffix(self):
        cross_repo = MagicMock()
        cross_repo.get_events_for_ticker.return_value = []
        svc = TechnicalAnalysisService(_history({}), cross_repo)

        assert svc.get_events_for_ticker("unk.is") == []
        cross_repo.get_events_for_ticker.assert_called_once_with("UNK")

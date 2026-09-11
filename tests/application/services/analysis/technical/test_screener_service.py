"""ScreenerService orkestrasyon testleri (mock repo + monkeypatch build_snapshot)."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from src.application.services.analysis.technical import screener_service as svc_module
from src.application.services.analysis.technical.screener import IndicatorSnapshot
from src.application.services.analysis.technical.screener_service import ScreenerService
from src.domain.models.daily_price import DailyPrice
from src.domain.models.stock import Stock

# İkisi de filter1 (rsi_oversold_above_ema200) ve filter2'yi (macd_bullish_cross_volume_spike)
# tetikler, filter3'ü (bollinger_lower_band_touch) tetiklemez.
_MATCHING_SNAPSHOT = IndicatorSnapshot(
    close=10.0, rsi14=20.0, ema200=9.0,
    macd_line=1.0, macd_signal=0.5, macd_line_prev=0.4, macd_signal_prev=0.5,
    volume=200.0, volume_sma20=100.0, bb_lower=9.5,
)

# Sadece filter3'ü (bollinger_lower_band_touch) tetikler.
_NON_MATCHING_SNAPSHOT = IndicatorSnapshot(
    close=10.0, rsi14=50.0, ema200=9.0,
    macd_line=0.1, macd_signal=0.5, macd_line_prev=0.6, macd_signal_prev=0.5,
    volume=50.0, volume_sma20=100.0, bb_lower=11.0,
)


def _stock(id_: int, ticker: str) -> Stock:
    return Stock(id=id_, ticker=ticker, name=ticker, currency_code="TRY")


def _dummy_rows(stock_id: int, n: int = 1) -> list[DailyPrice]:
    return [
        DailyPrice(id=None, stock_id=stock_id, price_date=date(2026, 1, 1) + timedelta(days=i), close_price=Decimal("10.0"))
        for i in range(n)
    ]


class TestScan:
    def test_matching_snapshot_returns_expected_filter_matches(self, monkeypatch):
        monkeypatch.setattr(svc_module, "build_snapshot", lambda *a, **kw: _MATCHING_SNAPSHOT)
        stock_repo = MagicMock()
        stock_repo.get_all_stocks.return_value = [_stock(1, "FROTO")]
        price_repo = MagicMock()
        price_repo.get_price_series.return_value = _dummy_rows(1)

        matches = ScreenerService(price_repo, stock_repo).scan()

        assert {m.filter_key for m in matches} == {
            "rsi_oversold_above_ema200",
            "macd_bullish_cross_volume_spike",
        }
        assert all(m.ticker == "FROTO" for m in matches)
        assert all(m.close_price == 10.0 for m in matches)

    def test_non_matching_snapshot_only_triggers_bollinger_filter(self, monkeypatch):
        monkeypatch.setattr(svc_module, "build_snapshot", lambda *a, **kw: _NON_MATCHING_SNAPSHOT)
        stock_repo = MagicMock()
        stock_repo.get_all_stocks.return_value = [_stock(1, "FROTO")]
        price_repo = MagicMock()
        price_repo.get_price_series.return_value = _dummy_rows(1)

        matches = ScreenerService(price_repo, stock_repo).scan()

        assert len(matches) == 1
        assert matches[0].filter_key == "bollinger_lower_band_touch"

    def test_filter_keys_restricts_evaluated_filters(self, monkeypatch):
        monkeypatch.setattr(svc_module, "build_snapshot", lambda *a, **kw: _MATCHING_SNAPSHOT)
        stock_repo = MagicMock()
        stock_repo.get_all_stocks.return_value = [_stock(1, "FROTO")]
        price_repo = MagicMock()
        price_repo.get_price_series.return_value = _dummy_rows(1)

        matches = ScreenerService(price_repo, stock_repo).scan(filter_keys=["rsi_oversold_above_ema200"])

        assert len(matches) == 1
        assert matches[0].filter_key == "rsi_oversold_above_ema200"

    def test_skips_stock_without_id(self, monkeypatch):
        called = MagicMock()
        monkeypatch.setattr(svc_module, "build_snapshot", called)
        stock_repo = MagicMock()
        stock_repo.get_all_stocks.return_value = [Stock(id=None, ticker="NOID", name="NOID", currency_code="TRY")]
        price_repo = MagicMock()

        matches = ScreenerService(price_repo, stock_repo).scan()

        assert matches == []
        called.assert_not_called()
        price_repo.get_price_series.assert_not_called()

    def test_skips_stock_with_no_price_rows(self):
        stock_repo = MagicMock()
        stock_repo.get_all_stocks.return_value = [_stock(1, "EMPTY")]
        price_repo = MagicMock()
        price_repo.get_price_series.return_value = []

        matches = ScreenerService(price_repo, stock_repo).scan()

        assert matches == []

    def test_aggregates_matches_across_multiple_stocks(self, monkeypatch):
        monkeypatch.setattr(svc_module, "build_snapshot", lambda *a, **kw: _MATCHING_SNAPSHOT)
        stock_repo = MagicMock()
        stock_repo.get_all_stocks.return_value = [_stock(1, "AAA"), _stock(2, "BBB")]
        price_repo = MagicMock()
        price_repo.get_price_series.return_value = _dummy_rows(1)

        matches = ScreenerService(price_repo, stock_repo).scan(filter_keys=["rsi_oversold_above_ema200"])

        assert {m.ticker for m in matches} == {"AAA", "BBB"}
        assert len(matches) == 2


class TestScanTicker:
    def test_returns_empty_when_stock_not_found(self):
        stock_repo = MagicMock()
        stock_repo.get_stock_by_ticker.return_value = None
        price_repo = MagicMock()

        matches = ScreenerService(price_repo, stock_repo).scan_ticker("YOK")

        assert matches == []

    def test_returns_matches_for_found_stock(self, monkeypatch):
        monkeypatch.setattr(svc_module, "build_snapshot", lambda *a, **kw: _MATCHING_SNAPSHOT)
        stock_repo = MagicMock()
        stock_repo.get_stock_by_ticker.return_value = _stock(1, "FROTO")
        price_repo = MagicMock()
        price_repo.get_price_series.return_value = _dummy_rows(1)

        matches = ScreenerService(price_repo, stock_repo).scan_ticker("froto", filter_keys=["bollinger_lower_band_touch"])

        assert matches == []  # matching snapshot bollinger'ı tetiklemiyor
        stock_repo.get_stock_by_ticker.assert_called_once_with("FROTO")

"""ScreenerService orkestrasyon testleri (mock DuckDB piyasa geçmişi + monkeypatch build_snapshot)."""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock

from src.application.services.analysis.technical import screener_service as svc_module
from src.application.services.analysis.technical.screener import IndicatorSnapshot
from src.application.services.analysis.technical.screener_service import ScreenerService
from src.domain.models.market_bar import MarketBar

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


def _bars(ticker: str, n: int = 1) -> list[MarketBar]:
    return [
        MarketBar(ticker=ticker, price_date=date(2026, 1, 1) + timedelta(days=i), close_price=10.0, volume=100)
        for i in range(n)
    ]


def _history(series: dict[str, list[MarketBar]]) -> MagicMock:
    history = MagicMock()
    history.list_tickers.return_value = list(series)
    history.get_price_series_bulk.side_effect = lambda tickers, start, end: {t: series[t] for t in tickers if t in series}
    history.get_price_series.side_effect = lambda ticker, start, end: series.get(ticker, [])
    return history


class TestScan:
    def test_matching_snapshot_returns_expected_filter_matches(self, monkeypatch):
        monkeypatch.setattr(svc_module, "build_snapshot", lambda *a, **kw: _MATCHING_SNAPSHOT)

        matches = ScreenerService(_history({"FROTO": _bars("FROTO")})).scan()

        assert {m.filter_key for m in matches} == {
            "rsi_oversold",
            "rsi_oversold_above_ema200",
            "macd_bullish_cross",
            "macd_bullish_cross_volume_spike",
            "volume_spike",
        }
        assert all(m.ticker == "FROTO" for m in matches)
        assert all(m.close_price == 10.0 for m in matches)

    def test_non_matching_snapshot_only_triggers_bollinger_filter(self, monkeypatch):
        monkeypatch.setattr(svc_module, "build_snapshot", lambda *a, **kw: _NON_MATCHING_SNAPSHOT)

        matches = ScreenerService(_history({"FROTO": _bars("FROTO")})).scan()

        assert len(matches) == 1
        assert matches[0].filter_key == "bollinger_lower_band_touch"

    def test_filter_keys_restricts_evaluated_filters(self, monkeypatch):
        monkeypatch.setattr(svc_module, "build_snapshot", lambda *a, **kw: _MATCHING_SNAPSHOT)

        matches = ScreenerService(_history({"FROTO": _bars("FROTO")})).scan(filter_keys=["rsi_oversold_above_ema200"])

        assert len(matches) == 1
        assert matches[0].filter_key == "rsi_oversold_above_ema200"

    def test_skips_ticker_with_no_bars(self):
        matches = ScreenerService(_history({"EMPTY": []})).scan()

        assert matches == []

    def test_aggregates_matches_across_multiple_tickers(self, monkeypatch):
        monkeypatch.setattr(svc_module, "build_snapshot", lambda *a, **kw: _MATCHING_SNAPSHOT)
        history = _history({"AAA": _bars("AAA"), "BBB": _bars("BBB")})

        matches = ScreenerService(history).scan(filter_keys=["rsi_oversold_above_ema200"])

        assert {m.ticker for m in matches} == {"AAA", "BBB"}
        assert len(matches) == 2

    def test_scans_whole_catalog_in_chunks(self, monkeypatch):
        monkeypatch.setattr(svc_module, "_SCAN_CHUNK", 2)
        monkeypatch.setattr(svc_module, "build_snapshot", lambda *a, **kw: _MATCHING_SNAPSHOT)
        tickers = [f"T{i:02d}" for i in range(5)]
        history = _history({t: _bars(t) for t in tickers})

        matches = ScreenerService(history).scan(filter_keys=["rsi_oversold_above_ema200"])

        assert {m.ticker for m in matches} == set(tickers)
        assert history.get_price_series_bulk.call_count == 3  # 2 + 2 + 1


class TestScanTicker:
    def test_returns_empty_when_no_data(self):
        assert ScreenerService(_history({})).scan_ticker("YOK") == []

    def test_returns_matches_for_found_ticker_and_strips_suffix(self, monkeypatch):
        monkeypatch.setattr(svc_module, "build_snapshot", lambda *a, **kw: _MATCHING_SNAPSHOT)
        history = _history({"FROTO": _bars("FROTO")})

        matches = ScreenerService(history).scan_ticker("froto.is", filter_keys=["bollinger_lower_band_touch"])

        assert matches == []  # matching snapshot bollinger'ı tetiklemiyor
        assert history.get_price_series.call_args.args[0] == "FROTO"

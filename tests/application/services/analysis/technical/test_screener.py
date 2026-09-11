"""build_snapshot ve screener filtreleri — saf vektörel hesap testleri."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from src.application.services.analysis.technical.screener import (
    SCREENER_FILTERS,
    IndicatorSnapshot,
    build_snapshot,
    is_macd_bullish_cross_with_volume_spike,
    is_rsi_oversold_above_ema200,
    is_touching_lower_bollinger_band,
)


def _make_series(values: list[float], start: date = date(2020, 1, 1)) -> pd.Series:
    idx = [start + timedelta(days=i) for i in range(len(values))]
    return pd.Series(values, index=idx)


class TestBuildSnapshot:
    def test_empty_closes_returns_none(self):
        empty = pd.Series([], dtype=float)
        assert build_snapshot(empty, empty, empty, empty) is None

    def test_sufficient_close_only_data_produces_snapshot(self):
        # 300 gün düz fiyat -> RSI/EMA200/MACD/Bollinger hesaplanabilir, OHLCV yok.
        closes = _make_series([100.0 + (i % 5) for i in range(300)])
        empty = pd.Series([], dtype=float)

        snap = build_snapshot(closes, empty, empty, empty)

        assert snap is not None
        assert snap.rsi14 is not None
        assert snap.ema200 is not None
        assert snap.macd_line is not None
        assert snap.bb_lower is not None
        # Hacim serisi boş verildi -> hacim-bağımlı alanlar None.
        assert snap.volume is None
        assert snap.volume_sma20 is None

    def test_ohlcv_present_populates_volume_fields(self):
        closes = _make_series([100.0 + (i % 5) for i in range(300)])
        highs = closes + 1.0
        lows = closes - 1.0
        volumes = _make_series([1000.0] * 300)

        snap = build_snapshot(closes, highs, lows, volumes)

        assert snap is not None
        assert snap.volume == pytest.approx(1000.0)
        assert snap.volume_sma20 == pytest.approx(1000.0)


class TestRsiOversoldAboveEma200Filter:
    def test_matches_when_oversold_and_above_trend(self):
        snap = IndicatorSnapshot(
            close=110.0, rsi14=25.0, ema200=100.0,
            macd_line=None, macd_signal=None, macd_line_prev=None, macd_signal_prev=None,
            volume=None, volume_sma20=None, bb_lower=None,
        )
        assert is_rsi_oversold_above_ema200(snap) is True

    def test_does_not_match_when_not_oversold(self):
        snap = IndicatorSnapshot(
            close=110.0, rsi14=50.0, ema200=100.0,
            macd_line=None, macd_signal=None, macd_line_prev=None, macd_signal_prev=None,
            volume=None, volume_sma20=None, bb_lower=None,
        )
        assert is_rsi_oversold_above_ema200(snap) is False

    def test_does_not_match_when_below_trend(self):
        snap = IndicatorSnapshot(
            close=90.0, rsi14=25.0, ema200=100.0,
            macd_line=None, macd_signal=None, macd_line_prev=None, macd_signal_prev=None,
            volume=None, volume_sma20=None, bb_lower=None,
        )
        assert is_rsi_oversold_above_ema200(snap) is False

    def test_missing_data_never_matches(self):
        snap = IndicatorSnapshot(
            close=110.0, rsi14=None, ema200=100.0,
            macd_line=None, macd_signal=None, macd_line_prev=None, macd_signal_prev=None,
            volume=None, volume_sma20=None, bb_lower=None,
        )
        assert is_rsi_oversold_above_ema200(snap) is False


class TestMacdBullishCrossVolumeSpikeFilter:
    def _snap(self, macd_line, macd_signal, macd_line_prev, macd_signal_prev, volume, volume_sma20):
        return IndicatorSnapshot(
            close=10.0, rsi14=None, ema200=None,
            macd_line=macd_line, macd_signal=macd_signal,
            macd_line_prev=macd_line_prev, macd_signal_prev=macd_signal_prev,
            volume=volume, volume_sma20=volume_sma20, bb_lower=None,
        )

    def test_matches_on_cross_up_with_volume_spike(self):
        snap = self._snap(1.0, 0.5, 0.4, 0.5, 200.0, 100.0)
        assert is_macd_bullish_cross_with_volume_spike(snap) is True

    def test_does_not_match_without_cross(self):
        snap = self._snap(1.0, 0.5, 0.6, 0.5, 200.0, 100.0)  # prev zaten line > signal, kesişim yok
        assert is_macd_bullish_cross_with_volume_spike(snap) is False

    def test_does_not_match_without_volume_spike(self):
        snap = self._snap(1.0, 0.5, 0.4, 0.5, 50.0, 100.0)
        assert is_macd_bullish_cross_with_volume_spike(snap) is False

    def test_missing_volume_never_matches(self):
        snap = self._snap(1.0, 0.5, 0.4, 0.5, None, None)
        assert is_macd_bullish_cross_with_volume_spike(snap) is False


class TestTouchingLowerBollingerBandFilter:
    def test_matches_when_close_at_or_below_lower_band(self):
        snap = IndicatorSnapshot(
            close=9.5, rsi14=None, ema200=None,
            macd_line=None, macd_signal=None, macd_line_prev=None, macd_signal_prev=None,
            volume=None, volume_sma20=None, bb_lower=9.5,
        )
        assert is_touching_lower_bollinger_band(snap) is True

    def test_does_not_match_when_above_lower_band(self):
        snap = IndicatorSnapshot(
            close=11.0, rsi14=None, ema200=None,
            macd_line=None, macd_signal=None, macd_line_prev=None, macd_signal_prev=None,
            volume=None, volume_sma20=None, bb_lower=9.5,
        )
        assert is_touching_lower_bollinger_band(snap) is False

    def test_missing_band_never_matches(self):
        snap = IndicatorSnapshot(
            close=9.5, rsi14=None, ema200=None,
            macd_line=None, macd_signal=None, macd_line_prev=None, macd_signal_prev=None,
            volume=None, volume_sma20=None, bb_lower=None,
        )
        assert is_touching_lower_bollinger_band(snap) is False


class TestScreenerFiltersRegistry:
    def test_registry_has_three_filters_with_labels_and_callables(self):
        assert len(SCREENER_FILTERS) == 3
        for filter_def in SCREENER_FILTERS.values():
            assert isinstance(filter_def.label, str) and filter_def.label
            assert callable(filter_def.predicate)

"""ADX ve Supertrend tarayıcı filtreleri ve snapshot alanları."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from src.application.services.analysis.technical.screener import (
    SCREENER_FILTERS,
    IndicatorSnapshot,
    build_snapshot,
    is_adx_strong_uptrend,
    is_supertrend_buy_signal,
)


def _make_series(values: list[float], start: date = date(2020, 1, 1)) -> pd.Series:
    idx = [start + timedelta(days=i) for i in range(len(values))]
    return pd.Series(values, index=idx)


def _snap(**overrides) -> IndicatorSnapshot:
    base = dict(
        close=10.0, rsi14=None, ema200=None,
        macd_line=None, macd_signal=None, macd_line_prev=None, macd_signal_prev=None,
        volume=None, volume_sma20=None, bb_lower=None,
    )
    base.update(overrides)
    return IndicatorSnapshot(**base)


def test_filters_are_registered():
    assert {"adx_strong_uptrend", "supertrend_buy_signal"} <= set(SCREENER_FILTERS)


class TestAdxStrongUptrendFilter:
    def test_matches_with_strong_trend_and_plus_di_above_minus_di(self):
        assert is_adx_strong_uptrend(_snap(adx14=30.0, plus_di14=28.0, minus_di14=12.0)) is True

    def test_does_not_match_with_weak_trend(self):
        assert is_adx_strong_uptrend(_snap(adx14=20.0, plus_di14=28.0, minus_di14=12.0)) is False

    def test_does_not_match_in_strong_downtrend(self):
        assert is_adx_strong_uptrend(_snap(adx14=35.0, plus_di14=10.0, minus_di14=30.0)) is False

    def test_missing_data_never_matches(self):
        assert is_adx_strong_uptrend(_snap()) is False


class TestSupertrendBuySignalFilter:
    def test_matches_when_direction_flips_up(self):
        assert is_supertrend_buy_signal(_snap(supertrend_direction=1, supertrend_direction_prev=-1)) is True

    def test_does_not_match_when_already_in_uptrend(self):
        assert is_supertrend_buy_signal(_snap(supertrend_direction=1, supertrend_direction_prev=1)) is False

    def test_does_not_match_in_downtrend(self):
        assert is_supertrend_buy_signal(_snap(supertrend_direction=-1, supertrend_direction_prev=-1)) is False

    def test_missing_direction_never_matches(self):
        assert is_supertrend_buy_signal(_snap()) is False


class TestBuildSnapshotTrendFields:
    def test_ohlc_populates_adx_and_supertrend(self):
        closes = _make_series([100.0 + 2.0 * i for i in range(300)])

        snap = build_snapshot(closes, closes + 1.0, closes - 1.0, _make_series([1000.0] * 300))

        assert snap.adx14 is not None and snap.adx14 > 25.0
        assert snap.plus_di14 > snap.minus_di14
        assert snap.supertrend_direction == 1
        assert snap.supertrend_direction_prev == 1
        assert is_adx_strong_uptrend(snap) is True
        assert is_supertrend_buy_signal(snap) is False

    def test_close_only_data_leaves_trend_fields_empty(self):
        closes = _make_series([100.0 + (i % 5) for i in range(300)])
        empty = pd.Series([], dtype=float)

        snap = build_snapshot(closes, empty, empty, empty)

        assert snap.adx14 is None
        assert snap.supertrend_direction is None
        assert is_adx_strong_uptrend(snap) is False
        assert is_supertrend_buy_signal(snap) is False

    def test_reversal_on_last_bar_gives_buy_signal(self):
        down = [300.0 - 2.0 * i for i in range(120)]
        # Düşüş boyunca Supertrend -1; son bar sert yükselişle yönü çevirir.
        closes = _make_series(down + [down[-1] + 80.0])

        snap = build_snapshot(closes, closes + 1.0, closes - 1.0, _make_series([1000.0] * 121))

        assert snap.supertrend_direction_prev == -1
        assert snap.supertrend_direction == 1
        assert is_supertrend_buy_signal(snap) is True

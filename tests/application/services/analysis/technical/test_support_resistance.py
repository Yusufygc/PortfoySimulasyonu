"""compute_support_resistance / find_pivot_* — saf fraktal pivot testleri."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from src.application.services.analysis.technical.support_resistance import (
    compute_support_resistance,
    find_pivot_highs,
    find_pivot_lows,
)


def _series(values: list[float], start: date = date(2020, 1, 1)) -> pd.Series:
    idx = [start + timedelta(days=i) for i in range(len(values))]
    return pd.Series(values, index=idx)


class TestFindPivotHighs:
    def test_detects_local_peaks_with_default_window(self):
        highs = _series([1, 2, 5, 2, 1, 2, 6, 2, 1, 2, 3, 2, 1])
        mask = find_pivot_highs(highs, left=2, right=2)
        peak_values = sorted(highs[mask].tolist())
        assert peak_values == [3.0, 5.0, 6.0]

    def test_edges_without_full_window_are_not_pivots(self):
        highs = _series([9, 1, 1, 1, 1])  # index 0'ın solunda 2 komşu yok
        mask = find_pivot_highs(highs, left=2, right=2)
        assert mask.iloc[0] == False  # noqa: E712


class TestFindPivotLows:
    def test_detects_local_troughs_with_default_window(self):
        lows = _series([5, 4, 1, 4, 5, 4, 0, 4, 5, 4, 2, 4, 5])
        mask = find_pivot_lows(lows, left=2, right=2)
        trough_values = sorted(lows[mask].tolist())
        assert trough_values == [0.0, 1.0, 2.0]


class TestComputeSupportResistance:
    def test_finds_nearest_support_and_resistance_around_price(self):
        highs = _series([1, 2, 5, 2, 1, 2, 6, 2, 1, 2, 3, 2, 1])
        lows = _series([5, 4, 1, 4, 5, 4, 0, 4, 5, 4, 2, 4, 5])
        closes = _series([2.5] * 13)

        support, resistance = compute_support_resistance(highs, lows, closes)

        assert support == pytest.approx(2.0)
        assert resistance == pytest.approx(3.0)

    def test_no_pivot_above_price_gives_none_resistance(self):
        highs = _series([1, 2, 5, 2, 1, 2, 6, 2, 1, 2, 3, 2, 1])
        lows = _series([5, 4, 1, 4, 5, 4, 0, 4, 5, 4, 2, 4, 5])
        closes = _series([10.0] * 13)  # tüm pivot high'ların üzerinde

        support, resistance = compute_support_resistance(highs, lows, closes)

        assert resistance is None
        assert support == pytest.approx(2.0)  # en yüksek pivot low hâlâ altında

    def test_empty_series_returns_none_none(self):
        empty = pd.Series([], dtype=float)
        assert compute_support_resistance(empty, empty, empty) == (None, None)

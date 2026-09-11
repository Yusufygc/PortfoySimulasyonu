"""compute_candlestick_bars — OHLC geometri testleri (görsel regresyon değil, bkz. plan §7.4)."""
from __future__ import annotations

import pytest

from src.ui_qml.charts.candlestick_mapper import OhlcBar, compute_candlestick_bars


class TestEdgeCases:
    def test_empty_bars_returns_empty_list(self):
        assert compute_candlestick_bars([], width=100, height=100) == []

    def test_zero_width_returns_empty_list(self):
        bars = [OhlcBar(10, 15, 5, 12)]
        assert compute_candlestick_bars(bars, width=0, height=100) == []


class TestSingleBar:
    def test_geometry_hand_computed(self):
        # open=10, high=15, low=5, close=12 -> bullish (close>=open)
        bars = [OhlcBar(open=10, high=15, low=5, close=12)]
        geometries = compute_candlestick_bars(bars, width=100, height=100, padding=0.0)

        assert len(geometries) == 1
        g = geometries[0]
        assert g.x_center == pytest.approx(50.0)
        assert g.bar_width == pytest.approx(60.0)  # slot_width=100, ratio=0.6
        assert g.wick_top_y == pytest.approx(0.0)     # high=15 -> tepe
        assert g.wick_bottom_y == pytest.approx(100.0)  # low=5 -> dip
        assert g.body_top_y == pytest.approx(30.0)    # max(10,12)=12 -> (1-0.7)*100
        assert g.body_bottom_y == pytest.approx(50.0)  # min(10,12)=10 -> (1-0.5)*100
        assert g.is_bullish is True

    def test_bearish_bar_when_close_below_open(self):
        bars = [OhlcBar(open=12, high=15, low=5, close=10)]
        geometries = compute_candlestick_bars(bars, width=100, height=100, padding=0.0)
        assert geometries[0].is_bullish is False

    def test_close_equal_open_counts_as_bullish(self):
        bars = [OhlcBar(open=10, high=12, low=8, close=10)]
        geometries = compute_candlestick_bars(bars, width=100, height=100, padding=0.0)
        assert geometries[0].is_bullish is True


class TestMultipleBars:
    def test_shared_scale_across_all_bars(self):
        # İkinci barın high'ı (30) ilk bar'ın ölçeğini de etkilemeli (ortak min/max).
        bars = [OhlcBar(10, 12, 8, 11), OhlcBar(20, 30, 15, 25)]
        geometries = compute_candlestick_bars(bars, width=100, height=100, padding=0.0)

        # min_low=8, max_high=30 -> range=22. Bar1 high=12 -> y=(1-(12-8)/22)*100
        assert geometries[0].wick_top_y == pytest.approx((1 - (12 - 8) / 22) * 100)
        assert geometries[1].wick_top_y == pytest.approx(0.0)  # bar2 high=30 -> tepe

    def test_x_centers_evenly_spaced(self):
        bars = [OhlcBar(10, 12, 8, 11) for _ in range(4)]
        geometries = compute_candlestick_bars(bars, width=100, height=100, padding=0.0)
        x_centers = [g.x_center for g in geometries]
        assert x_centers == pytest.approx([12.5, 37.5, 62.5, 87.5])

    def test_flat_range_centers_wicks_vertically(self):
        bars = [OhlcBar(10, 10, 10, 10), OhlcBar(10, 10, 10, 10)]
        geometries = compute_candlestick_bars(bars, width=100, height=100, padding=0.0)
        for g in geometries:
            assert g.wick_top_y == pytest.approx(50.0)
            assert g.wick_bottom_y == pytest.approx(50.0)

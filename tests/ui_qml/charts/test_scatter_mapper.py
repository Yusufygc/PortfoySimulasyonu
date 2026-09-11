"""compute_scatter_points — risk/getiri saçılım geometri testleri (bkz. plan §7.4)."""
from __future__ import annotations

import pytest

from src.ui_qml.charts.scatter_mapper import compute_scatter_points


class TestEdgeCases:
    def test_empty_values_returns_empty_list(self):
        assert compute_scatter_points([], [], width=100, height=100) == []

    def test_mismatched_lengths_returns_empty_list(self):
        assert compute_scatter_points([1.0, 2.0], [1.0], width=100, height=100) == []

    def test_zero_width_returns_empty_list(self):
        assert compute_scatter_points([1.0], [1.0], width=0, height=100) == []


class TestSinglePoint:
    def test_single_point_centers_on_both_axes(self):
        points = compute_scatter_points([5.0], [5.0], width=100, height=100, padding=0.0)
        assert points == [pytest.approx((50.0, 50.0))]


class TestMultiplePoints:
    def test_x_left_to_right_y_inverted(self):
        # x: 0..10, y: 0..10 -> nokta1 (x=0,y=0) sol-alt, nokta2 (x=10,y=10) sağ-üst
        points = compute_scatter_points([0.0, 10.0], [0.0, 10.0], width=100, height=100, padding=0.0)
        (x1, y1), (x2, y2) = points
        assert x1 == pytest.approx(0.0)
        assert y1 == pytest.approx(100.0)  # y=0 (en düşük getiri) -> alt
        assert x2 == pytest.approx(100.0)
        assert y2 == pytest.approx(0.0)  # y=10 (en yüksek getiri) -> üst

    def test_flat_x_range_centers_horizontally(self):
        points = compute_scatter_points([5.0, 5.0], [0.0, 10.0], width=100, height=100, padding=0.0)
        for x, _y in points:
            assert x == pytest.approx(50.0)

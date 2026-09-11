"""compute_bar_geometry — bar grafiği geometri testleri (görsel regresyon değil, bkz. plan §7.4)."""
from __future__ import annotations

import pytest

from src.ui_qml.charts.bar_mapper import compute_bar_geometry


class TestEdgeCases:
    def test_empty_values_returns_empty_list(self):
        assert compute_bar_geometry([], width=100, height=100) == []

    def test_zero_width_returns_empty_list(self):
        assert compute_bar_geometry([1.0], width=0, height=100) == []

    def test_zero_height_returns_empty_list(self):
        assert compute_bar_geometry([1.0], width=100, height=0) == []


class TestAllPositive:
    def test_zero_line_included_in_scale(self):
        # values 0..10 -> range 0..10 dahil (min(0,..)=0), value=10 tepe (y=0)
        geometries = compute_bar_geometry([10.0], width=100, height=100, padding=0.0)
        g = geometries[0]
        assert g.bar_top_y == pytest.approx(0.0)
        assert g.bar_bottom_y == pytest.approx(100.0)  # sıfır çizgisi -> taban
        assert g.is_positive is True


class TestMixedSign:
    def test_positive_and_negative_share_zero_baseline(self):
        geometries = compute_bar_geometry([10.0, -10.0], width=100, height=100, padding=0.0)
        pos, neg = geometries
        # range = -10..10 -> zero_y = 50 (orta)
        assert pos.bar_top_y == pytest.approx(0.0)
        assert pos.bar_bottom_y == pytest.approx(50.0)
        assert pos.is_positive is True

        assert neg.bar_top_y == pytest.approx(50.0)
        assert neg.bar_bottom_y == pytest.approx(100.0)
        assert neg.is_positive is False

    def test_zero_value_counts_as_positive(self):
        geometries = compute_bar_geometry([0.0], width=100, height=100, padding=0.0)
        assert geometries[0].is_positive is True


class TestLayout:
    def test_x_centers_evenly_spaced(self):
        geometries = compute_bar_geometry([1.0, 2.0, 3.0, 4.0], width=100, height=100, padding=0.0)
        x_centers = [g.x_center for g in geometries]
        assert x_centers == pytest.approx([12.5, 37.5, 62.5, 87.5])

    def test_bar_width_uses_ratio_of_slot_width(self):
        geometries = compute_bar_geometry([1.0, 2.0], width=100, height=100, padding=0.0, bar_width_ratio=0.5)
        assert geometries[0].bar_width == pytest.approx(25.0)  # slot_width=50, ratio=0.5

    def test_all_zero_values_centers_baseline_vertically(self):
        geometries = compute_bar_geometry([0.0, 0.0], width=100, height=100, padding=0.0)
        for g in geometries:
            assert g.bar_top_y == pytest.approx(50.0)
            assert g.bar_bottom_y == pytest.approx(50.0)

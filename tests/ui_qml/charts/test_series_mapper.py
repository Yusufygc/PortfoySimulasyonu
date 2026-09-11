"""map_series_to_points — nokta/koordinat eşleme testleri (görsel regresyon değil, bkz. plan §7.4)."""
from __future__ import annotations

import pytest

from src.ui_qml.charts.series_mapper import map_series_to_points


class TestEdgeCases:
    def test_empty_values_returns_empty_list(self):
        assert map_series_to_points([], width=100, height=50) == []

    def test_zero_width_returns_empty_list(self):
        assert map_series_to_points([1, 2, 3], width=0, height=50) == []

    def test_negative_height_returns_empty_list(self):
        assert map_series_to_points([1, 2, 3], width=100, height=-10) == []

    def test_single_value_is_centered(self):
        points = map_series_to_points([42.0], width=100, height=50, padding=0.0)
        assert points == [(50.0, 25.0)]


class TestHorizontalSpacing:
    def test_x_coordinates_evenly_spaced_across_width(self):
        points = map_series_to_points([1, 2, 3, 4, 5], width=100, height=50, padding=0.0)
        xs = [x for x, _ in points]
        assert xs == pytest.approx([0.0, 25.0, 50.0, 75.0, 100.0])

    def test_padding_shrinks_plot_area(self):
        points = map_series_to_points([1, 2], width=100, height=50, padding=10.0)
        xs = [x for x, _ in points]
        assert xs == pytest.approx([10.0, 90.0])


class TestVerticalMapping:
    def test_flat_series_maps_to_vertical_midpoint(self):
        points = map_series_to_points([5, 5, 5], width=100, height=50, padding=0.0)
        ys = [y for _, y in points]
        assert ys == pytest.approx([25.0, 25.0, 25.0])

    def test_higher_value_maps_to_smaller_y_top_of_chart(self):
        # Ekran y-ekseni ters: en yüksek değer en küçük y (grafiğin üstü).
        points = map_series_to_points([0, 100], width=100, height=50, padding=0.0)
        (_, y_low), (_, y_high_value) = points
        assert y_low == pytest.approx(50.0)  # düşük değer -> alt (büyük y)
        assert y_high_value == pytest.approx(0.0)  # yüksek değer -> üst (küçük y)

    def test_monotonically_rising_series_maps_to_monotonically_falling_y(self):
        points = map_series_to_points([10, 20, 30, 40], width=100, height=50, padding=0.0)
        ys = [y for _, y in points]
        assert ys == sorted(ys, reverse=True)


class TestExplicitValueBounds:
    def test_value_bounds_override_series_own_min_max(self):
        # Seri kendi başına [0,50] arasında ama ortak ölçek [0,100] verildi -> yarı yükseklikte kalmalı.
        points = map_series_to_points([0, 50], width=100, height=100, padding=0.0, value_bounds=(0.0, 100.0))
        ys = [y for _, y in points]
        assert ys == pytest.approx([100.0, 50.0])

    def test_shared_bounds_keep_two_series_comparable(self):
        # MACD hattı + sinyal hattı aynı value_bounds ile çizilirse, aynı ham değer aynı y'ye düşer.
        bounds = (-5.0, 5.0)
        macd_points = map_series_to_points([2.0, 3.0], width=100, height=100, padding=0.0, value_bounds=bounds)
        signal_points = map_series_to_points([2.0, 1.0], width=100, height=100, padding=0.0, value_bounds=bounds)
        assert macd_points[0][1] == pytest.approx(signal_points[0][1])  # ikisi de değer=2.0 -> aynı y

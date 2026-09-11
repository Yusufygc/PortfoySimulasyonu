"""compute_treemap_rects — squarified treemap geometri testleri (bkz. plan §7.4)."""
from __future__ import annotations

import pytest

from src.ui_qml.charts.treemap_mapper import compute_treemap_rects


class TestEdgeCases:
    def test_empty_items_returns_empty_list(self):
        assert compute_treemap_rects([], width=100, height=100) == []

    def test_zero_width_returns_empty_list(self):
        assert compute_treemap_rects([("A", 1.0, 5.0)], width=0, height=100) == []

    def test_zero_or_negative_weights_are_filtered_out(self):
        rects = compute_treemap_rects([("A", 1.0, 5.0), ("B", 0.0, 3.0), ("C", -2.0, 1.0)], width=100, height=100, padding=0.0)
        assert [r.label for r in rects] == ["A"]

    def test_all_non_positive_weights_returns_empty_list(self):
        assert compute_treemap_rects([("A", 0.0, 5.0)], width=100, height=100) == []


class TestSingleItem:
    def test_single_item_fills_entire_plot_area(self):
        rects = compute_treemap_rects([("A", 10.0, 42.0)], width=100, height=100, padding=0.0)
        assert len(rects) == 1
        r = rects[0]
        assert r.x == pytest.approx(0.0)
        assert r.y == pytest.approx(0.0)
        assert r.width == pytest.approx(100.0)
        assert r.height == pytest.approx(100.0)
        assert r.value == 42.0
        assert r.label == "A"

    def test_padding_shrinks_plot_area(self):
        rects = compute_treemap_rects([("A", 10.0, 0.0)], width=100, height=100, padding=10.0)
        r = rects[0]
        assert r.x == pytest.approx(10.0)
        assert r.y == pytest.approx(10.0)
        assert r.width == pytest.approx(80.0)
        assert r.height == pytest.approx(80.0)


class TestTwoEqualItems:
    def test_equal_weights_on_square_split_into_two_horizontal_rows(self):
        # Kare tuval + eşit ağırlık -> worst-ratio eşitliğinde tek satırda birleşip
        # tam genişlikte iki yatay şerit olarak dizilir (elle hesaplanmış: her ikisinin
        # de worst aspect ratio'su 2.0 - `<=` birleştirme koşulunu tetikler).
        rects = compute_treemap_rects([("A", 1.0, 1.0), ("B", 1.0, -1.0)], width=100, height=100, padding=0.0)
        assert len(rects) == 2
        a, b = rects
        assert a.label == "A"
        assert (a.x, a.y, a.width, a.height) == pytest.approx((0.0, 0.0, 100.0, 50.0))
        assert b.label == "B"
        assert (b.x, b.y, b.width, b.height) == pytest.approx((0.0, 50.0, 100.0, 50.0))


class TestInvariants:
    def test_total_area_conserved_across_many_items(self):
        items = [(f"S{i}", float(i + 1), float(i)) for i in range(6)]
        rects = compute_treemap_rects(items, width=200.0, height=120.0, padding=0.0)
        assert len(rects) == 6
        total_area = sum(r.width * r.height for r in rects)
        assert total_area == pytest.approx(200.0 * 120.0, rel=1e-6)

    def test_all_rects_have_positive_dimensions(self):
        items = [(f"S{i}", float(i + 1), float(i)) for i in range(6)]
        rects = compute_treemap_rects(items, width=200.0, height=120.0, padding=8.0)
        for r in rects:
            assert r.width > 0
            assert r.height > 0

    def test_every_label_appears_exactly_once(self):
        items = [("A", 5.0, 1.0), ("B", 3.0, 2.0), ("C", 2.0, 3.0), ("D", 1.0, 4.0)]
        rects = compute_treemap_rects(items, width=150.0, height=100.0, padding=0.0)
        assert sorted(r.label for r in rects) == ["A", "B", "C", "D"]

    def test_larger_weight_gets_larger_area(self):
        items = [("Big", 8.0, 0.0), ("Small", 1.0, 0.0)]
        rects = compute_treemap_rects(items, width=180.0, height=90.0, padding=0.0)
        by_label = {r.label: r for r in rects}
        assert (by_label["Big"].width * by_label["Big"].height) > (by_label["Small"].width * by_label["Small"].height)

"""compute_donut_segments — açı hesaplama testleri (görsel regresyon değil, bkz. plan §7.4)."""
from __future__ import annotations

import pytest

from src.ui_qml.charts.donut_mapper import compute_donut_segments


class TestEdgeCases:
    def test_empty_weights_returns_empty_list(self):
        assert compute_donut_segments([]) == []

    def test_all_zero_weights_returns_empty_list(self):
        assert compute_donut_segments([0.0, 0.0]) == []

    def test_negative_total_returns_empty_list(self):
        assert compute_donut_segments([-5.0, -3.0]) == []


class TestSegments:
    def test_three_weights_sum_to_360_degrees(self):
        segments = compute_donut_segments([50.0, 30.0, 20.0])
        total_span = sum(span for _, span in segments)
        assert total_span == pytest.approx(360.0)

    def test_segment_spans_proportional_to_weights(self):
        segments = compute_donut_segments([50.0, 30.0, 20.0])
        spans = [span for _, span in segments]
        assert spans == pytest.approx([180.0, 108.0, 72.0])

    def test_segments_are_contiguous_starting_at_zero(self):
        segments = compute_donut_segments([50.0, 30.0, 20.0])
        starts = [start for start, _ in segments]
        assert starts == pytest.approx([0.0, 180.0, 288.0])

    def test_equal_weights_split_evenly(self):
        segments = compute_donut_segments([1.0, 1.0, 1.0, 1.0])
        spans = [span for _, span in segments]
        assert spans == pytest.approx([90.0, 90.0, 90.0, 90.0])

    def test_negative_weight_gets_zero_span_but_others_unaffected(self):
        segments = compute_donut_segments([-10.0, 50.0, 50.0])
        spans = [span for _, span in segments]
        assert spans == pytest.approx([0.0, 180.0, 180.0])

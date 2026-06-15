"""Enflasyon saf-matematik modülü birim testleri."""
from __future__ import annotations

import pytest

from src.application.services.analysis.financials.inflation import (
    get_yoy_tufe,
    period_to_month,
    real_growth,
)


class TestPeriodToMonth:
    def test_single_digit_month(self):
        assert period_to_month("2026/3") == "2026-03"

    def test_double_digit_month(self):
        assert period_to_month("2025/12") == "2025-12"

    def test_june(self):
        assert period_to_month("2024/6") == "2024-06"


class TestRealGrowth:
    def test_positive_real_growth(self):
        result = real_growth(80.0, 65.0)
        assert abs(result - 9.09) < 0.01

    def test_zero_nominal(self):
        result = real_growth(0.0, 50.0)
        assert abs(result - (-33.33)) < 0.01

    def test_none_nominal(self):
        assert real_growth(None, 50.0) is None

    def test_none_tufe(self):
        assert real_growth(80.0, None) is None

    def test_both_none(self):
        assert real_growth(None, None) is None


class TestGetYoyTufe:
    _INDEX = {
        "2024-03": 1600.0,
        "2023-03": 1000.0,
        "2024-06": 1650.0,
    }

    def test_yoy_calculation(self):
        result = get_yoy_tufe("2024/3", self._INDEX)
        assert result is not None
        assert abs(result - 60.0) < 0.01

    def test_missing_current_month(self):
        assert get_yoy_tufe("2024/9", self._INDEX) is None

    def test_missing_prev_year(self):
        assert get_yoy_tufe("2022/3", self._INDEX) is None

"""Risk metrikleri motoru — saf hesap testleri (bkz. TRANSFORMATION_PLAN.md §9.3)."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List

import pytest

from src.application.services.analysis.risk_metrics import (
    compute_calmar_ratio,
    compute_conditional_var_pct,
    compute_daily_return_vector,
    compute_max_drawdown_pct,
    compute_monthly_returns_matrix,
    compute_omega_ratio,
    compute_r_squared,
    compute_sortino_ratio,
    compute_tracking_error,
    compute_value_at_risk_pct,
)


def _business_days(start: date, n: int) -> List[date]:
    days: List[date] = []
    current = start
    while len(days) < n:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def _series(values: List[float], start: date = date(2024, 1, 1)) -> Dict[date, Decimal]:
    days = _business_days(start, len(values))
    return {d: Decimal(str(v)) for d, v in zip(days, values)}


class TestSortinoRatio:
    def test_empty_series_returns_none(self):
        assert compute_sortino_ratio({}) is None

    def test_no_downside_returns_none(self):
        # Sadece kazanç var -> downside_deviation=0 -> tanımsız (None)
        series = _series([100.0, 110.0, 120.0, 130.0])
        assert compute_sortino_ratio(series, risk_free_rate=0.0) is None

    def test_known_value_with_zero_risk_free_rate(self):
        series = _series([100.0, 110.0, 90.0, 120.0, 100.0])
        result = compute_sortino_ratio(series, risk_free_rate=0.0)
        assert result == pytest.approx(2.73, abs=0.02)


class TestCalmarRatio:
    def test_empty_series_returns_none(self):
        assert compute_calmar_ratio({}) is None

    def test_no_drawdown_returns_none(self):
        series = _series([100.0, 110.0, 120.0, 130.0])
        assert compute_calmar_ratio(series) is None

    def test_known_value_approx(self):
        # 100 -> (dip 80) -> 200, ~365 gün: CAGR≈%100, max_dd=-%20 -> Calmar≈5.0
        series = {
            date(2023, 1, 1): Decimal("100"),
            date(2023, 7, 1): Decimal("80"),
            date(2024, 1, 1): Decimal("200"),
        }
        result = compute_calmar_ratio(series)
        assert result == pytest.approx(5.0, rel=0.05)


class TestOmegaRatio:
    def test_empty_series_returns_none(self):
        assert compute_omega_ratio({}) is None

    def test_all_losses_gives_zero(self):
        # Hiç kazanç yok -> gains=0 -> omega=0.0 (bölen sıfır olmadığı için None değil)
        series = _series([100.0, 90.0, 80.0])
        assert compute_omega_ratio(series) == pytest.approx(0.0)

    def test_known_value(self):
        # returns: +0.10, -0.10, +0.10 -> gains=0.20, losses=0.10 -> omega=2.0
        series = _series([100.0, 110.0, 99.0, 108.9])
        result = compute_omega_ratio(series, target_return=0.0)
        assert result == pytest.approx(2.0, abs=1e-3)


class TestValueAtRisk:
    def test_insufficient_data_returns_none(self):
        assert compute_value_at_risk_pct(_series([100.0])) is None

    def test_known_percentile_confidence_80(self):
        # returns sırasıyla: -0.05, -0.02, +0.01, +0.03, +0.04
        series = _series([100.0, 95.0, 93.1, 94.031, 96.85193, 100.7460])
        result = compute_value_at_risk_pct(series, confidence=0.8)
        assert result == pytest.approx(-2.0, abs=1e-2)

    def test_known_percentile_confidence_95(self):
        series = _series([100.0, 95.0, 93.1, 94.031, 96.85193, 100.7460])
        result = compute_value_at_risk_pct(series, confidence=0.95)
        assert result == pytest.approx(-5.0, abs=1e-2)


class TestConditionalValueAtRisk:
    def test_insufficient_data_returns_none(self):
        assert compute_conditional_var_pct(_series([100.0])) is None

    def test_known_expected_shortfall(self):
        series = _series([100.0, 95.0, 93.1, 94.031, 96.85193, 100.7460])
        result = compute_conditional_var_pct(series, confidence=0.8)
        # kuyruk: [-0.05, -0.02] -> ortalama -0.035 -> %-3.5
        assert result == pytest.approx(-3.5, abs=1e-2)

    def test_cvar_is_never_better_than_var(self):
        series = _series([100.0, 95.0, 93.1, 94.031, 96.85193, 100.7460])
        var = compute_value_at_risk_pct(series, confidence=0.9)
        cvar = compute_conditional_var_pct(series, confidence=0.9)
        assert cvar <= var


class TestRSquared:
    def test_insufficient_data_returns_none(self):
        assert compute_r_squared({}, {}) is None

    def test_perfect_correlation_is_one(self):
        portfolio = _series([100.0, 110.0, 90.0, 120.0])
        # Sabit bir katsayıyla ölçeklenmiş seri, birebir aynı yüzde getiriyi üretir -> korelasyon 1 -> R²=1
        benchmark = _series([200.0, 220.0, 180.0, 240.0])
        result = compute_r_squared(portfolio, benchmark)
        assert result == pytest.approx(1.0, abs=1e-6)

    def test_r_squared_bounded_between_0_and_1(self):
        portfolio = _series([100.0, 105.0, 98.0, 110.0, 107.0])
        benchmark = _series([200.0, 198.0, 205.0, 203.0, 210.0])
        result = compute_r_squared(portfolio, benchmark)
        assert 0.0 <= result <= 1.0


class TestTrackingError:
    def test_insufficient_data_returns_none(self):
        assert compute_tracking_error({}, {}) is None

    def test_identical_series_has_zero_tracking_error(self):
        portfolio = _series([100.0, 105.0, 98.0, 110.0])
        benchmark = _series([100.0, 105.0, 98.0, 110.0])
        result = compute_tracking_error(portfolio, benchmark)
        assert result == pytest.approx(0.0, abs=1e-9)

    def test_diverging_series_has_positive_tracking_error(self):
        portfolio = _series([100.0, 110.0, 90.0, 130.0])
        benchmark = _series([100.0, 101.0, 99.0, 102.0])
        result = compute_tracking_error(portfolio, benchmark)
        assert result > 0.0


class TestMonthlyReturnsMatrix:
    def test_empty_series_returns_empty_dict(self):
        assert compute_monthly_returns_matrix({}) == {}

    def test_single_month_has_no_return_entries(self):
        series = {date(2024, 1, 5): Decimal("100"), date(2024, 1, 20): Decimal("110")}
        assert compute_monthly_returns_matrix(series) == {}

    def test_known_multi_month_returns(self):
        series = {
            date(2024, 1, 31): Decimal("100"),
            date(2024, 2, 29): Decimal("110"),  # +%10
            date(2024, 3, 31): Decimal("99"),   # -%10
        }
        result = compute_monthly_returns_matrix(series)
        assert result == {2024: {2: pytest.approx(10.0), 3: pytest.approx(-10.0)}}

    def test_uses_last_observation_of_each_month_as_month_end(self):
        series = {
            date(2024, 1, 10): Decimal("100"),
            date(2024, 1, 31): Decimal("105"),  # Ocak ay-sonu değeri bu olmalı
            date(2024, 2, 28): Decimal("115"),  # (115-105)/105*100
        }
        result = compute_monthly_returns_matrix(series)
        assert result[2024][2] == pytest.approx(((115 - 105) / 105) * 100)


class TestDailyReturnVectorHelper:
    """Yeni metriklerin dayandığı yardımcı — dolaylı olarak zaten test ediliyor,
    burada sadece temel sözleşmesi (contract) doğrulanıyor."""

    def test_empty_series_returns_empty_list(self):
        assert compute_daily_return_vector({}) == []

    def test_single_point_returns_empty_list(self):
        assert compute_daily_return_vector(_series([100.0])) == []


class TestMaxDrawdownHelperUsedByCalmar:
    def test_no_drawdown_when_monotonically_rising(self):
        series = _series([100.0, 110.0, 120.0])
        assert compute_max_drawdown_pct(series) == pytest.approx(0.0)

    def test_known_drawdown_value(self):
        series = {
            date(2024, 1, 1): Decimal("100"),
            date(2024, 1, 2): Decimal("80"),
            date(2024, 1, 3): Decimal("200"),
        }
        assert compute_max_drawdown_pct(series) == pytest.approx(-20.0)

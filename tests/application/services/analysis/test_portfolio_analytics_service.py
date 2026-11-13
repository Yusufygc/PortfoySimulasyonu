"""PortfolioAnalyticsService — AnalysisService delege + yeni panel/risk metrik testleri."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List
from unittest.mock import MagicMock

import pytest

from src.application.services.analysis.models import (
    AnalysisFilterState,
    BenchmarkSeries,
    ComparisonViewDTO,
)
from src.application.services.analysis.portfolio_analytics_service import (
    PortfolioAnalyticsService,
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


def _filter_state() -> AnalysisFilterState:
    return AnalysisFilterState(start_date=date(2024, 1, 1), end_date=date(2024, 3, 1))


def _comparison_dto(with_benchmark: bool = True) -> ComparisonViewDTO:
    portfolio_values = [100.0 + i * 0.5 + (i % 4) for i in range(60)]
    portfolio_series = _series(portfolio_values)
    benchmark_series = []
    if with_benchmark:
        benchmark_values = [100.0 + i * 0.3 for i in range(60)]
        benchmark_series = [BenchmarkSeries(code="xu100", label="XU100", points=_series(benchmark_values))]
    stock_series = {"AKBNK": _series([50.0 + i * 0.2 for i in range(60)])}
    comparison_portfolios = [
        BenchmarkSeries(code="model:1", label="Model Portföy", points=_series([90.0 + i * 0.4 for i in range(60)])),
    ]
    return ComparisonViewDTO(
        portfolio_series=portfolio_series,
        benchmark_series=benchmark_series,
        stock_series=stock_series,
        comparison_metrics=[],
        comparison_portfolios=comparison_portfolios,
        current_portfolio_label="Portföyüm",
        warnings=[],
    )


class TestPassThrough:
    def test_get_overview_delegates(self):
        analysis_service = MagicMock()
        analysis_service.get_overview.return_value = "overview-dto"
        svc = PortfolioAnalyticsService(analysis_service)
        state = _filter_state()

        result = svc.get_overview(state)

        assert result == "overview-dto"
        analysis_service.get_overview.assert_called_once_with(state, bundle=None)

    def test_get_comparison_view_delegates(self):
        analysis_service = MagicMock()
        analysis_service.get_comparison_view.return_value = "comparison-dto"
        svc = PortfolioAnalyticsService(analysis_service)
        state = _filter_state()

        result = svc.get_comparison_view(state, selected_benchmarks=["xu100"])

        assert result == "comparison-dto"
        analysis_service.get_comparison_view.assert_called_once_with(state, ["xu100"], bundle=None)

    def test_get_allocation_risk_view_delegates(self):
        analysis_service = MagicMock()
        analysis_service.get_allocation_risk_view.return_value = "risk-dto"
        svc = PortfolioAnalyticsService(analysis_service)
        state = _filter_state()

        assert svc.get_allocation_risk_view(state) == "risk-dto"
        analysis_service.get_allocation_risk_view.assert_called_once_with(state, bundle=None)

    def test_simple_getters_delegate(self):
        analysis_service = MagicMock()
        analysis_service.get_benchmark_definitions.return_value = ["b"]
        analysis_service.get_portfolio_options.return_value = ["p"]
        analysis_service.get_first_trade_date_for_source.return_value = date(2020, 1, 1)
        analysis_service.get_stock_map_for_source.return_value = {1: "AKBNK"}
        svc = PortfolioAnalyticsService(analysis_service)

        assert svc.get_benchmark_definitions() == ["b"]
        assert svc.get_portfolio_options() == ["p"]
        assert svc.get_first_trade_date_for_source("dashboard") == date(2020, 1, 1)
        assert svc.get_stock_map_for_source("dashboard") == {1: "AKBNK"}


class TestGetChartPanels:
    def test_builds_all_six_panels_from_comparison(self):
        svc = PortfolioAnalyticsService(MagicMock())
        comparison = _comparison_dto()

        panels = svc.get_chart_panels(_filter_state(), comparison=comparison)

        expected_labels = {"Portföyüm", "XU100", "AKBNK", "Model Portföy"}
        assert expected_labels.issubset(set(panels.aligned_series.columns))
        assert not panels.drawdowns.empty
        assert (panels.drawdowns <= 0.0001).all().all()  # drawdown hep <= 0
        assert isinstance(panels.risk_return_metrics, dict)
        for col in expected_labels:
            assert "annual_volatility_pct" in panels.risk_return_metrics[col]
            assert "total_return_pct" in panels.risk_return_metrics[col]
        assert panels.comparison is comparison

    def test_uses_get_comparison_view_when_not_supplied(self):
        analysis_service = MagicMock()
        comparison = _comparison_dto()
        analysis_service.get_comparison_view.return_value = comparison
        svc = PortfolioAnalyticsService(analysis_service)

        panels = svc.get_chart_panels(_filter_state())

        analysis_service.get_comparison_view.assert_called_once()
        assert panels.comparison is comparison


class TestGetExtendedRiskMetrics:
    def test_computes_full_metrics_with_benchmark(self):
        svc = PortfolioAnalyticsService(MagicMock())
        comparison = _comparison_dto(with_benchmark=True)

        metrics = svc.get_extended_risk_metrics(_filter_state(), comparison=comparison)

        assert metrics.sharpe_ratio is not None
        assert metrics.sortino_ratio is not None
        assert metrics.calmar_ratio is not None
        assert metrics.omega_ratio is not None
        assert metrics.value_at_risk_95_pct is not None
        assert metrics.conditional_var_95_pct is not None
        assert metrics.beta is not None
        assert metrics.alpha is not None
        assert metrics.r_squared is not None
        assert metrics.tracking_error_pct is not None
        assert metrics.monthly_returns_matrix  # en az bir ay
        assert metrics.benchmark_label == "XU100"

    def test_benchmark_dependent_metrics_are_none_without_benchmark(self):
        svc = PortfolioAnalyticsService(MagicMock())
        comparison = _comparison_dto(with_benchmark=False)

        metrics = svc.get_extended_risk_metrics(_filter_state(), comparison=comparison)

        assert metrics.beta is None
        assert metrics.alpha is None
        assert metrics.r_squared is None
        assert metrics.tracking_error_pct is None
        assert metrics.benchmark_label is None
        # Benchmark'a bağlı olmayan metrikler yine hesaplanır:
        assert metrics.sharpe_ratio is not None
        assert metrics.sortino_ratio is not None

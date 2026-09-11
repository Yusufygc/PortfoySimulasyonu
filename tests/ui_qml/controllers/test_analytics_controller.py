"""AnalyticsController — d4 Karşılaştırma Laboratuvarı köprüsü testleri."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.application.services.analysis.models import BenchmarkSeries, ComparisonMetric, ComparisonViewDTO
from src.application.services.analysis.portfolio_analytics_service import ChartPanelsDTO, ExtendedRiskMetricsDTO
from src.ui_qml.controllers.analytics_controller import AnalyticsController

_DATES = pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31"])


def _comparison(with_benchmark: bool = True) -> ComparisonViewDTO:
    benchmarks = [BenchmarkSeries(code="bist100", label="BIST 100", points={})] if with_benchmark else []
    return ComparisonViewDTO(
        portfolio_series={},
        benchmark_series=benchmarks,
        stock_series={},
        comparison_metrics=[
            ComparisonMetric(label="BIST 100", portfolio_return_pct=21.0, benchmark_return_pct=0.0, relative_gap_pct=21.0),
        ],
        comparison_portfolios=[],
        current_portfolio_label="Ana Portföy",
        warnings=[],
    )


def _panels(with_benchmark: bool = True) -> ChartPanelsDTO:
    columns = {"Ana Portföy": [200.0, 220.0, 242.0]}
    risk_return = {"Ana Portföy": {"annual_volatility_pct": 15.0, "total_return_pct": 21.0}}
    if with_benchmark:
        columns["BIST 100"] = [100.0, 105.0, 100.0]
        risk_return["BIST 100"] = {"annual_volatility_pct": 10.0, "total_return_pct": 0.0}

    aligned = pd.DataFrame(columns, index=_DATES)
    drawdowns = pd.DataFrame({"Ana Portföy": [0.0, -5.0, -2.0]}, index=_DATES)
    periodic_returns = pd.DataFrame({"Ana Portföy": [10.0, 10.0]}, index=_DATES[1:])

    return ChartPanelsDTO(
        aligned_series=aligned,
        drawdowns=drawdowns,
        periodic_returns=periodic_returns,
        risk_return_metrics=risk_return,
        comparison=_comparison(with_benchmark),
    )


def _extended(**overrides) -> ExtendedRiskMetricsDTO:
    defaults = dict(
        sharpe_ratio=1.5, sortino_ratio=2.0, calmar_ratio=0.8, omega_ratio=1.3,
        value_at_risk_95_pct=-3.2, conditional_var_95_pct=-4.5, beta=0.19, alpha=2.1,
        r_squared=0.10, tracking_error_pct=23.1,
        monthly_returns_matrix={2024: {1: 5.0, 3: -2.0}},
        benchmark_label="BIST 100",
    )
    defaults.update(overrides)
    return ExtendedRiskMetricsDTO(**defaults)


def _make_container(panels=None, extended=None) -> MagicMock:
    container = MagicMock()
    container.portfolio_analytics_service.get_first_trade_date_for_source.return_value = date(2024, 1, 1)
    container.portfolio_analytics_service.get_chart_panels.return_value = panels if panels is not None else _panels()
    container.portfolio_analytics_service.get_extended_risk_metrics.return_value = extended if extended is not None else _extended()
    return container


class TestPerformancePanel:
    def test_values_normalized_to_base_100(self, qapp):
        controller = AnalyticsController(_make_container())
        assert controller.portfolioPerformanceValues == pytest.approx([100.0, 110.0, 121.0])
        assert controller.benchmarkPerformanceValues == pytest.approx([100.0, 105.0, 100.0])
        assert controller.benchmarkLabel == "BIST 100"

    def test_no_benchmark_gives_empty_series_and_label(self, qapp):
        container = _make_container(panels=_panels(with_benchmark=False))
        controller = AnalyticsController(container)
        assert controller.benchmarkLabel == ""
        assert controller.benchmarkPerformanceValues == []


class TestSummaryPanel:
    def test_parallel_lists_from_comparison_metrics(self, qapp):
        controller = AnalyticsController(_make_container())
        assert controller.summaryLabels == ["BIST 100"]
        assert controller.summaryPortfolioReturnPct == [21.0]
        assert controller.summaryBenchmarkReturnPct == [0.0]
        assert controller.summaryRelativeGapPct == [21.0]


class TestDrawdownPanel:
    def test_drawdown_values_from_portfolio_column(self, qapp):
        controller = AnalyticsController(_make_container())
        assert controller.drawdownValues == [0.0, -5.0, -2.0]


class TestPeriodicReturnsPanel:
    def test_labels_formatted_as_year_month(self, qapp):
        controller = AnalyticsController(_make_container())
        assert controller.periodicReturnLabels == ["2024-02", "2024-03"]
        assert controller.periodicReturnValues == [10.0, 10.0]


class TestScatterPanel:
    def test_labels_and_points_from_risk_return_metrics(self, qapp):
        controller = AnalyticsController(_make_container())
        assert controller.scatterLabels == ["Ana Portföy", "BIST 100"]
        assert controller.scatterVolatilityPct == [15.0, 10.0]
        assert controller.scatterReturnPct == [21.0, 0.0]


class TestTreemapPanel:
    def test_items_built_from_risk_return_metrics(self, qapp):
        controller = AnalyticsController(_make_container())
        assert controller.treemapItems == [
            {"label": "Ana Portföy", "weight": 21.0, "value": 21.0},
            {"label": "BIST 100", "weight": 1.0, "value": 0.0},
        ]

    def test_negative_return_weight_uses_absolute_value(self, qapp):
        panels = _panels()
        panels.risk_return_metrics["Ana Portföy"]["total_return_pct"] = -30.0
        controller = AnalyticsController(_make_container(panels=panels))
        item = controller.treemapItems[0]
        assert item["weight"] == 30.0
        assert item["value"] == -30.0

    def test_zero_return_gets_floor_weight_of_one(self, qapp):
        panels = _panels()
        panels.risk_return_metrics["BIST 100"]["total_return_pct"] = 0.0
        controller = AnalyticsController(_make_container(panels=panels))
        by_label = {item["label"]: item for item in controller.treemapItems}
        assert by_label["BIST 100"]["weight"] == 1.0


class TestExtendedRiskMetrics:
    def test_all_metrics_exposed_as_floats(self, qapp):
        controller = AnalyticsController(_make_container())
        assert controller.sharpeRatio == 1.5
        assert controller.sortinoRatio == 2.0
        assert controller.calmarRatio == 0.8
        assert controller.omegaRatio == 1.3
        assert controller.valueAtRisk95Pct == -3.2
        assert controller.conditionalVar95Pct == -4.5
        assert controller.beta == 0.19
        assert controller.alpha == 2.1
        assert controller.rSquared == 0.10
        assert controller.trackingErrorPct == 23.1

    def test_none_metrics_default_to_zero(self, qapp):
        container = _make_container(extended=_extended(
            sharpe_ratio=None, sortino_ratio=None, calmar_ratio=None, omega_ratio=None,
            value_at_risk_95_pct=None, conditional_var_95_pct=None, beta=None, alpha=None,
            r_squared=None, tracking_error_pct=None,
        ))
        controller = AnalyticsController(container)
        assert controller.sharpeRatio == 0.0
        assert controller.beta == 0.0
        assert controller.trackingErrorPct == 0.0


class TestMonthlyHeatmap:
    def test_missing_months_filled_with_sentinel(self, qapp):
        controller = AnalyticsController(_make_container())
        assert controller.monthlyHeatmapYears == [2024]
        rows = controller.monthlyHeatmapRows
        assert len(rows) == 1
        assert rows[0][0] == 5.0    # Ocak
        assert rows[0][2] == -2.0   # Mart
        assert rows[0][1] == -9999.0  # Şubat -> veri yok


class TestRefresh:
    def test_refresh_recomputes_all_panels(self, qapp):
        container = _make_container()
        controller = AnalyticsController(container)
        assert controller.sharpeRatio == 1.5

        container.portfolio_analytics_service.get_extended_risk_metrics.return_value = _extended(sharpe_ratio=3.0)
        controller.refresh()

        assert controller.sharpeRatio == 3.0

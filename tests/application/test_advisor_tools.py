"""advisor_tools.py — Gemini tool-calling araçları testleri (bkz. plan §6.2, e1.1)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.application.services.ai.advisor_tools import build_tool_specs
from src.application.services.analysis.models import AllocationItem, AllocationRiskDTO, AnalysisOverviewDTO
from src.application.services.analysis.portfolio_analytics_service import ExtendedRiskMetricsDTO  # noqa: F401 (referans)
from src.application.services.planning.risk_optimization_bridge_service import RiskAwareOptimizationResult
from src.domain.models.optimization_result import OptimizationMetrics, OptimizationResult, OptimizationSuggestion
from src.domain.models.risk_profile import RiskLabel


def _overview_dto() -> AnalysisOverviewDTO:
    return AnalysisOverviewDTO(
        total_value=Decimal("598908.23"), period_return_pct=-13.88, benchmark_gap_pct=-45.71,
        benchmark_label="BIST 100", largest_position_label="MERKO.IS", largest_position_weight_pct=19.85,
        best_contributor_label="PSGYO.IS", best_contributor_pct=18.77, worst_contributor_label="OBAMS.IS",
        worst_contributor_pct=-32.92, max_drawdown_pct=-28.14, insights=[], warnings=["uyarı1"],
        portfolio_label="Ana Portföy",
    )


def _risk_view_dto() -> AllocationRiskDTO:
    return AllocationRiskDTO(
        items=[AllocationItem(label="AKBNK", cost_value=1000.0, current_value=1200.0, weight_pct=60.0)],
        top_three_weight_pct=100.0, volatility_pct=22.4, max_drawdown_pct=-28.14,
        concentration_label="Yüksek", warnings=[], sharpe_ratio=-2.08, beta=0.72, alpha=-45.9,
    )


def _optimization_outcome(risk_label=RiskLabel.DENGELI, is_manual_override=False) -> RiskAwareOptimizationResult:
    result = OptimizationResult(
        current_metrics=OptimizationMetrics(expected_return=0.10, volatility=0.294, sharpe_ratio=-1.03),
        optimized_metrics=OptimizationMetrics(expected_return=0.30, volatility=0.389, sharpe_ratio=0.015),
        suggestions=[
            OptimizationSuggestion(symbol="RUZYE.IS", current_weight=12.23, optimal_weight=28.0, change=15.77, action="EKLE"),
            OptimizationSuggestion(symbol="MERKO.IS", current_weight=11.71, optimal_weight=0.0, change=-11.71, action="AZALT"),
        ],
        min_volatility_metrics=OptimizationMetrics(expected_return=-0.07, volatility=0.288, sharpe_ratio=-1.28),
    )
    return RiskAwareOptimizationResult(
        result=result, risk_label=risk_label, max_single_weight_pct=20.0, equity_ceiling_pct=30,
        used_default_profile=False, is_manual_override=is_manual_override,
    )


def _make_services(
    overview=None, risk_view=None, optimization_outcome=None, optimization_raises=None,
    stock_overview=None, technical=None,
):
    portfolio_analytics_service = MagicMock()
    portfolio_analytics_service.get_first_trade_date_for_source.return_value = date(2024, 1, 1)
    portfolio_analytics_service.get_overview.return_value = overview or _overview_dto()
    portfolio_analytics_service.get_allocation_risk_view.return_value = risk_view or _risk_view_dto()

    risk_optimization_bridge_service = MagicMock()
    if optimization_raises is not None:
        risk_optimization_bridge_service.optimize_dashboard_portfolio_with_risk_profile.side_effect = optimization_raises
    else:
        risk_optimization_bridge_service.optimize_dashboard_portfolio_with_risk_profile.return_value = (
            optimization_outcome or _optimization_outcome()
        )

    stock_360_service = MagicMock()
    stock_360_service.get_overview.return_value = stock_overview
    stock_360_service.get_technical_levels.return_value = technical

    return portfolio_analytics_service, risk_optimization_bridge_service, stock_360_service


def _specs_by_name(portfolio_analytics_service, risk_optimization_bridge_service, stock_360_service):
    specs = build_tool_specs(portfolio_analytics_service, risk_optimization_bridge_service, stock_360_service)
    return {spec.name: spec for spec in specs}


class TestToolRegistryShape:
    def test_four_tools_registered(self):
        services = _make_services()
        specs = _specs_by_name(*services)
        assert set(specs.keys()) == {
            "get_portfolio_overview", "get_allocation_and_risk", "suggest_optimization", "get_stock_overview",
        }

    def test_each_spec_has_description_and_schema(self):
        services = _make_services()
        for spec in build_tool_specs(*services):
            assert spec.description
            assert spec.parameters_schema["type"] == "object"

    def test_get_stock_overview_requires_ticker_in_schema(self):
        services = _make_services()
        specs = _specs_by_name(*services)
        assert specs["get_stock_overview"].parameters_schema["required"] == ["ticker"]

    def test_suggest_optimization_risk_label_is_enum_of_valid_labels(self):
        services = _make_services()
        specs = _specs_by_name(*services)
        enum_values = set(specs["suggest_optimization"].parameters_schema["properties"]["risk_label"]["enum"])
        assert enum_values == {"COK_MUHAFAZAKAR", "MUHAFAZAKAR", "DENGELI", "BUYUME_ODAKLI", "AGRESIF"}


class TestGetPortfolioOverview:
    def test_handler_maps_dto_fields(self):
        services = _make_services()
        handler = _specs_by_name(*services)["get_portfolio_overview"].handler

        result = handler({})

        assert result["portfolio_label"] == "Ana Portföy"
        assert result["total_value_try"] == pytest.approx(598908.23)
        assert result["period_return_pct"] == -13.88
        assert result["benchmark_label"] == "BIST 100"
        assert result["largest_position_label"] == "MERKO.IS"
        assert result["warnings"] == ["uyarı1"]

    def test_uses_dashboard_default_filter_state(self):
        services = _make_services()
        portfolio_analytics_service = services[0]
        handler = _specs_by_name(*services)["get_portfolio_overview"].handler

        handler({})

        filter_state = portfolio_analytics_service.get_overview.call_args.args[0]
        assert filter_state.portfolio_source == "dashboard"
        assert filter_state.selected_benchmarks == ["bist100"]


class TestGetAllocationAndRisk:
    def test_handler_maps_items_and_metrics(self):
        services = _make_services()
        handler = _specs_by_name(*services)["get_allocation_and_risk"].handler

        result = handler({})

        assert result["items"] == [{"label": "AKBNK", "weight_pct": 60.0, "current_value_try": 1200.0}]
        assert result["volatility_pct"] == 22.4
        assert result["sharpe_ratio"] == -2.08
        assert result["beta"] == 0.72


class TestSuggestOptimization:
    def test_handler_maps_metrics_and_suggestions(self):
        services = _make_services()
        handler = _specs_by_name(*services)["suggest_optimization"].handler

        result = handler({})

        assert result["applied_risk_label"] == RiskLabel.DENGELI
        assert result["current"]["expected_return_pct"] == pytest.approx(10.0)
        assert result["optimized"]["expected_return_pct"] == pytest.approx(30.0)
        assert result["min_volatility"]["volatility_pct"] == pytest.approx(28.8)
        assert result["suggestions"] == [
            {"symbol": "RUZYE.IS", "current_weight_pct": 12.23, "optimal_weight_pct": 28.0, "change_pct": 15.77, "action": "EKLE"},
            {"symbol": "MERKO.IS", "current_weight_pct": 11.71, "optimal_weight_pct": 0.0, "change_pct": -11.71, "action": "AZALT"},
        ]

    def test_valid_risk_label_override_is_forwarded(self):
        services = _make_services()
        risk_optimization_bridge_service = services[1]
        handler = _specs_by_name(*services)["suggest_optimization"].handler

        handler({"risk_label": "AGRESIF"})

        call = risk_optimization_bridge_service.optimize_dashboard_portfolio_with_risk_profile.call_args
        assert call.kwargs["risk_label_override"] == "AGRESIF"

    def test_unknown_risk_label_is_ignored_not_fabricated(self):
        services = _make_services()
        risk_optimization_bridge_service = services[1]
        handler = _specs_by_name(*services)["suggest_optimization"].handler

        handler({"risk_label": "UYDURMA_ETIKET"})

        call = risk_optimization_bridge_service.optimize_dashboard_portfolio_with_risk_profile.call_args
        assert call.kwargs["risk_label_override"] is None

    def test_no_min_volatility_metrics_gives_none(self):
        outcome = _optimization_outcome()
        outcome.result.suggestions.clear()
        object.__setattr__(outcome.result, "min_volatility_metrics", None)
        services = _make_services(optimization_outcome=outcome)
        handler = _specs_by_name(*services)["suggest_optimization"].handler

        result = handler({})

        assert result["min_volatility"] is None

    def test_backend_exception_is_captured_as_error_dict(self):
        services = _make_services(optimization_raises=ValueError("Optimizasyon icin en az 2 hisse gerekli."))
        handler = _specs_by_name(*services)["suggest_optimization"].handler

        result = handler({})

        assert "en az 2" in result["error"]


class TestGetStockOverview:
    def test_missing_ticker_returns_error(self):
        services = _make_services()
        handler = _specs_by_name(*services)["get_stock_overview"].handler
        result = handler({})
        assert "ticker" in result["error"].lower()

    def test_unknown_ticker_returns_error(self):
        services = _make_services(stock_overview=None)
        handler = _specs_by_name(*services)["get_stock_overview"].handler
        result = handler({"ticker": "YOK"})
        assert "bulunamadı" in result["error"]

    def test_ticker_is_uppercased_and_stripped(self):
        from src.application.services.analysis.stock_360_service import StockOverview

        overview = StockOverview(
            ticker="AKBNK", last_price=Decimal("120.5"), last_price_date=date(2026, 9, 1),
            daily_change_pct=1.5, volume=1000000, week52_low=Decimal("90"), week52_high=Decimal("150"),
        )
        services = _make_services(stock_overview=overview)
        stock_360_service = services[2]
        handler = _specs_by_name(*services)["get_stock_overview"].handler

        result = handler({"ticker": "  akbnk  "})

        stock_360_service.get_overview.assert_called_once_with("AKBNK")
        assert result["ticker"] == "AKBNK"
        assert result["last_price"] == pytest.approx(120.5)
        assert result["last_price_date"] == "2026-09-01"

    def test_technical_levels_merged_when_available(self):
        from src.application.services.analysis.stock_360_service import StockOverview, TechnicalLevels

        overview = StockOverview(
            ticker="AKBNK", last_price=Decimal("120"), last_price_date=date(2026, 9, 1),
            daily_change_pct=1.5, volume=1000, week52_low=Decimal("90"), week52_high=Decimal("150"),
        )
        technical = TechnicalLevels(
            ticker="AKBNK", rsi14=28.0, macd_line=0.4, macd_signal=0.1,
            sma50=110.0, sma200=100.0, ema20=115.0, support=105.0, resistance=125.0,
        )
        services = _make_services(stock_overview=overview, technical=technical)
        handler = _specs_by_name(*services)["get_stock_overview"].handler

        result = handler({"ticker": "AKBNK"})

        assert result["rsi14"] == 28.0
        assert result["support"] == 105.0

    def test_missing_technical_levels_does_not_crash(self):
        from src.application.services.analysis.stock_360_service import StockOverview

        overview = StockOverview(
            ticker="AKBNK", last_price=Decimal("120"), last_price_date=date(2026, 9, 1),
            daily_change_pct=1.5, volume=1000, week52_low=Decimal("90"), week52_high=Decimal("150"),
        )
        services = _make_services(stock_overview=overview, technical=None)
        handler = _specs_by_name(*services)["get_stock_overview"].handler

        result = handler({"ticker": "AKBNK"})

        assert "rsi14" not in result
        assert result["ticker"] == "AKBNK"

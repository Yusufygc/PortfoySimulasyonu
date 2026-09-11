"""OptimizationController — d5 OptimizationView köprüsü testleri."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.application.services.planning.risk_optimization_bridge_service import RiskAwareOptimizationResult
from src.domain.models.optimization_result import OptimizationMetrics, OptimizationResult, OptimizationSuggestion
from src.domain.models.risk_profile import RiskLabel
from src.ui_qml.controllers.optimization_controller import OptimizationController


def _metrics(expected_return=0.15, volatility=0.20, sharpe_ratio=0.75) -> OptimizationMetrics:
    return OptimizationMetrics(expected_return=expected_return, volatility=volatility, sharpe_ratio=sharpe_ratio)


def _outcome(
    risk_label=RiskLabel.DENGELI,
    max_single_weight_pct=20.0,
    equity_ceiling_pct=30,
    used_default_profile=False,
    is_manual_override=False,
    suggestions=None,
) -> RiskAwareOptimizationResult:
    result = OptimizationResult(
        current_metrics=_metrics(0.10, 0.25, 0.40),
        optimized_metrics=_metrics(0.18, 0.22, 0.82),
        suggestions=suggestions if suggestions is not None else [
            OptimizationSuggestion(symbol="AKBNK", current_weight=60.0, optimal_weight=40.0, change=-20.0, action="AZALT"),
            OptimizationSuggestion(symbol="THYAO", current_weight=40.0, optimal_weight=60.0, change=20.0, action="EKLE"),
        ],
        min_volatility_metrics=_metrics(0.08, 0.15, 0.53),
    )
    return RiskAwareOptimizationResult(
        result=result, risk_label=risk_label, max_single_weight_pct=max_single_weight_pct,
        equity_ceiling_pct=equity_ceiling_pct, used_default_profile=used_default_profile,
        is_manual_override=is_manual_override,
    )


def _make_container(profile_risk_label=RiskLabel.DENGELI, model_portfolios=None, outcome=None, raises=None):
    container = MagicMock()
    profile = SimpleNamespace(risk_label=profile_risk_label) if profile_risk_label is not None else None
    container.risk_optimization_bridge_service.get_active_risk_profile.return_value = profile
    container.optimization_service.get_model_portfolios.return_value = model_portfolios or []

    if raises is not None:
        container.risk_optimization_bridge_service.optimize_dashboard_portfolio_with_risk_profile.side_effect = raises
        container.risk_optimization_bridge_service.optimize_model_portfolio_with_risk_profile.side_effect = raises
    else:
        result = outcome or _outcome()
        container.risk_optimization_bridge_service.optimize_dashboard_portfolio_with_risk_profile.return_value = result
        container.risk_optimization_bridge_service.optimize_model_portfolio_with_risk_profile.return_value = result
    return container


class TestSources:
    def test_dashboard_always_first_source(self, qapp):
        controller = OptimizationController(_make_container())
        assert controller.sourceLabels[0] == "Dashboard Portföyü"

    def test_model_portfolios_appended(self, qapp):
        portfolios = [SimpleNamespace(id=1, name="Uzun Vadeli"), SimpleNamespace(id=2, name="Spek")]
        controller = OptimizationController(_make_container(model_portfolios=portfolios))
        assert controller.sourceLabels == ["Dashboard Portföyü", "Uzun Vadeli", "Spek"]

    def test_select_source_by_index_switches_to_model_portfolio(self, qapp):
        portfolios = [SimpleNamespace(id=7, name="Uzun Vadeli")]
        container = _make_container(model_portfolios=portfolios)
        controller = OptimizationController(container)

        controller.selectSourceByIndex(1)
        controller.runOptimization()

        call = container.risk_optimization_bridge_service.optimize_model_portfolio_with_risk_profile.call_args
        assert call.kwargs["portfolio_id"] == 7


class TestSliderDefault:
    def test_defaults_to_saved_profile_label_index(self, qapp):
        controller = OptimizationController(_make_container(profile_risk_label=RiskLabel.AGRESIF))
        assert controller.sliderIndex == 4  # AGRESIF son sırada

    def test_no_saved_profile_defaults_to_dengeli(self, qapp):
        controller = OptimizationController(_make_container(profile_risk_label=None))
        assert controller.sliderIndex == 2  # DENGELI ortada


class TestSliderOverride:
    def test_untouched_slider_does_not_pass_override(self, qapp):
        container = _make_container()
        controller = OptimizationController(container)
        controller.runOptimization()

        call = container.risk_optimization_bridge_service.optimize_dashboard_portfolio_with_risk_profile.call_args
        assert call.kwargs["risk_label_override"] is None

    def test_touched_slider_passes_override(self, qapp):
        container = _make_container()
        controller = OptimizationController(container)

        controller.setSliderIndex(4)  # AGRESIF
        controller.runOptimization()

        call = container.risk_optimization_bridge_service.optimize_dashboard_portfolio_with_risk_profile.call_args
        assert call.kwargs["risk_label_override"] == RiskLabel.AGRESIF

    def test_slider_index_clamped_to_valid_range(self, qapp):
        controller = OptimizationController(_make_container())
        controller.setSliderIndex(99)
        assert controller.sliderIndex == 4
        controller.setSliderIndex(-5)
        assert controller.sliderIndex == 0


class TestResultMetrics:
    def test_metrics_converted_to_percent(self, qapp):
        controller = OptimizationController(_make_container())
        assert controller.currentReturnPct == pytest.approx(10.0)
        assert controller.currentVolatilityPct == pytest.approx(25.0)
        assert controller.currentSharpe == pytest.approx(0.40)
        assert controller.optimizedReturnPct == pytest.approx(18.0)
        assert controller.minVolatilityReturnPct == pytest.approx(8.0)
        assert controller.minVolatilityVolatilityPct == pytest.approx(15.0)

    def test_frontier_parallel_lists_have_three_points(self, qapp):
        controller = OptimizationController(_make_container())
        assert controller.frontierLabels == ["Mevcut", "Min. Risk", "Maks. Sharpe"]
        assert len(controller.frontierVolatilityPct) == 3
        assert len(controller.frontierReturnPct) == 3
        assert controller.frontierVolatilityPct[1] == pytest.approx(15.0)  # Min. Risk

    def test_policy_info_exposed(self, qapp):
        controller = OptimizationController(_make_container(outcome=_outcome(
            risk_label=RiskLabel.AGRESIF, max_single_weight_pct=35.0, equity_ceiling_pct=55,
        )))
        assert controller.activeRiskLabelDisplay == "Agresif"
        assert controller.maxSingleWeightPct == pytest.approx(35.0)
        assert controller.equityCeilingPct == pytest.approx(55.0)

    def test_none_equity_ceiling_uses_sentinel(self, qapp):
        controller = OptimizationController(_make_container(outcome=_outcome(equity_ceiling_pct=None)))
        assert controller.equityCeilingPct == -1.0


class TestSuggestions:
    def test_parallel_lists_from_suggestions(self, qapp):
        controller = OptimizationController(_make_container())
        assert controller.suggestionTickers == ["AKBNK", "THYAO"]
        assert controller.suggestionCurrentWeightPct == [60.0, 40.0]
        assert controller.suggestionOptimalWeightPct == [40.0, 60.0]
        assert controller.suggestionChangePct == [-20.0, 20.0]
        assert controller.suggestionActions == ["AZALT", "EKLE"]


class TestErrorHandling:
    def test_insufficient_positions_error_is_captured(self, qapp):
        container = _make_container(raises=ValueError("Optimizasyon icin portfoyde en az 2 farkli hisse olmalidir."))
        controller = OptimizationController(container)

        assert controller.hasResult is False
        assert "en az 2" in controller.errorMessage

    def test_successful_rerun_clears_previous_error(self, qapp):
        container = _make_container(raises=ValueError("gecici hata"))
        controller = OptimizationController(container)
        assert controller.hasResult is False

        container.risk_optimization_bridge_service.optimize_dashboard_portfolio_with_risk_profile.side_effect = None
        container.risk_optimization_bridge_service.optimize_dashboard_portfolio_with_risk_profile.return_value = _outcome()
        controller.runOptimization()

        assert controller.hasResult is True
        assert controller.errorMessage == ""

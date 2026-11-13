"""RiskOptimizationBridgeService — Risk Profili ↔ Optimizasyon Köprüsü testleri (bkz. plan §5.3)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.application.services.planning.optimization_market_data import OptimizationPolicy
from src.application.services.planning.risk_optimization_bridge_service import (
    MAX_SINGLE_WEIGHT_BY_LABEL,
    RISK_LABELS_ORDERED,
    RiskOptimizationBridgeService,
    max_single_weight_for_label,
)
from src.domain.models.risk_profile import RiskLabel


def _profile(risk_label: str):
    profile = MagicMock()
    profile.risk_label = risk_label
    return profile


def _make_bridge(risk_profile=None, base_policy=OptimizationPolicy(risk_free_rate=0.35, trading_days_per_year=252)):
    risk_profile_service = MagicMock()
    risk_profile_service.get_current_profile.return_value = risk_profile
    optimization_service = MagicMock()
    optimization_service.policy = base_policy
    optimization_service.optimize_dashboard_portfolio.return_value = "dashboard-result"
    optimization_service.optimize_model_portfolio.return_value = "model-result"
    return RiskOptimizationBridgeService(risk_profile_service, optimization_service), optimization_service


class TestMaxSingleWeightForLabel:
    def test_all_five_labels_mapped(self):
        for label in (
            RiskLabel.COK_MUHAFAZAKAR, RiskLabel.MUHAFAZAKAR, RiskLabel.DENGELI,
            RiskLabel.BUYUME_ODAKLI, RiskLabel.AGRESIF,
        ):
            assert label in MAX_SINGLE_WEIGHT_BY_LABEL

    def test_muhafazakar_and_agresif_match_plan_spec(self):
        # Plan §5.3: Muhafazakar tek-hisse max %10, Agresif tek-hisse max %35.
        assert max_single_weight_for_label(RiskLabel.MUHAFAZAKAR) == pytest.approx(0.10)
        assert max_single_weight_for_label(RiskLabel.AGRESIF) == pytest.approx(0.35)

    def test_weights_increase_monotonically_with_risk_appetite(self):
        ordered = [
            max_single_weight_for_label(label) for label in (
                RiskLabel.COK_MUHAFAZAKAR, RiskLabel.MUHAFAZAKAR, RiskLabel.DENGELI,
                RiskLabel.BUYUME_ODAKLI, RiskLabel.AGRESIF,
            )
        ]
        assert ordered == sorted(ordered)

    def test_unknown_label_falls_back_to_optimization_service_default(self):
        from src.application.services.planning.optimization_service import OptimizationService
        assert max_single_weight_for_label("BILINMEYEN") == OptimizationService.MAX_SINGLE_WEIGHT


class TestOptimizeDashboardPortfolioWithRiskProfile:
    def test_applies_risk_label_max_weight_and_preserves_base_policy_fields(self):
        bridge, optimization_service = _make_bridge(risk_profile=_profile(RiskLabel.AGRESIF))

        outcome = bridge.optimize_dashboard_portfolio_with_risk_profile()

        assert outcome.result == "dashboard-result"
        assert outcome.risk_label == RiskLabel.AGRESIF
        assert outcome.max_single_weight_pct == pytest.approx(35.0)
        assert outcome.equity_ceiling_pct == 55  # PROFILE_INFO[AGRESIF]["allocation"]["Hisse"]
        assert outcome.used_default_profile is False

        called_policy = optimization_service.optimize_dashboard_portfolio.call_args.kwargs["policy"]
        assert called_policy.max_single_weight == pytest.approx(0.35)
        assert called_policy.risk_free_rate == pytest.approx(0.35)  # base_policy'den korunmuş

    def test_no_saved_profile_falls_back_to_dengeli_default(self):
        bridge, optimization_service = _make_bridge(risk_profile=None)

        outcome = bridge.optimize_dashboard_portfolio_with_risk_profile()

        assert outcome.risk_label == RiskLabel.DENGELI
        assert outcome.max_single_weight_pct == pytest.approx(20.0)
        assert outcome.used_default_profile is True

    def test_muhafazakar_profile_gets_tight_cap(self):
        bridge, optimization_service = _make_bridge(risk_profile=_profile(RiskLabel.MUHAFAZAKAR))

        outcome = bridge.optimize_dashboard_portfolio_with_risk_profile()

        assert outcome.max_single_weight_pct == pytest.approx(10.0)
        assert outcome.equity_ceiling_pct == 20  # PROFILE_INFO[MUHAFAZAKAR]["allocation"]["Hisse"]


class TestOptimizeModelPortfolioWithRiskProfile:
    def test_forwards_portfolio_id_and_price_lookup_with_risk_policy(self):
        bridge, optimization_service = _make_bridge(risk_profile=_profile(RiskLabel.BUYUME_ODAKLI))
        price_lookup = object()

        outcome = bridge.optimize_model_portfolio_with_risk_profile(portfolio_id=42, price_lookup_func=price_lookup)

        assert outcome.result == "model-result"
        assert outcome.risk_label == RiskLabel.BUYUME_ODAKLI
        assert outcome.max_single_weight_pct == pytest.approx(28.0)
        optimization_service.optimize_model_portfolio.assert_called_once()
        call = optimization_service.optimize_model_portfolio.call_args
        assert call.args == (42, price_lookup)
        assert call.kwargs["policy"].max_single_weight == pytest.approx(0.28)


class TestRiskLabelOverride:
    def test_override_ignores_saved_profile_and_marks_manual(self):
        bridge, optimization_service = _make_bridge(risk_profile=_profile(RiskLabel.DENGELI))

        outcome = bridge.optimize_dashboard_portfolio_with_risk_profile(risk_label_override=RiskLabel.AGRESIF)

        assert outcome.risk_label == RiskLabel.AGRESIF
        assert outcome.max_single_weight_pct == pytest.approx(35.0)
        assert outcome.used_default_profile is False
        assert outcome.is_manual_override is True

    def test_no_override_is_not_manual(self):
        bridge, _ = _make_bridge(risk_profile=_profile(RiskLabel.DENGELI))
        outcome = bridge.optimize_dashboard_portfolio_with_risk_profile()
        assert outcome.is_manual_override is False

    def test_unknown_override_label_falls_back_to_saved_profile(self):
        bridge, _ = _make_bridge(risk_profile=_profile(RiskLabel.AGRESIF))
        outcome = bridge.optimize_dashboard_portfolio_with_risk_profile(risk_label_override="GECERSIZ")
        assert outcome.risk_label == RiskLabel.AGRESIF
        assert outcome.is_manual_override is False

    def test_model_portfolio_override_forwarded(self):
        bridge, optimization_service = _make_bridge(risk_profile=_profile(RiskLabel.DENGELI))

        outcome = bridge.optimize_model_portfolio_with_risk_profile(
            portfolio_id=7, risk_label_override=RiskLabel.COK_MUHAFAZAKAR,
        )

        assert outcome.risk_label == RiskLabel.COK_MUHAFAZAKAR
        assert outcome.max_single_weight_pct == pytest.approx(8.0)
        assert outcome.is_manual_override is True

    def test_risk_labels_ordered_from_conservative_to_aggressive(self):
        assert RISK_LABELS_ORDERED == (
            RiskLabel.COK_MUHAFAZAKAR, RiskLabel.MUHAFAZAKAR, RiskLabel.DENGELI,
            RiskLabel.BUYUME_ODAKLI, RiskLabel.AGRESIF,
        )


class TestGetActiveRiskProfile:
    def test_delegates_to_risk_profile_service(self):
        profile = _profile(RiskLabel.DENGELI)
        bridge, _ = _make_bridge(risk_profile=profile)

        assert bridge.get_active_risk_profile() is profile

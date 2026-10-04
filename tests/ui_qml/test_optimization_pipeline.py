"""Optimizasyon hesap hattı ve grafik HTML üreticileri."""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.ui_qml.controllers import optimization_chart_html as charts
from src.ui_qml.controllers import optimization_pipeline as pipeline


def _metrics(ret, vol, sharpe):
    return SimpleNamespace(expected_return=ret, volatility=vol, sharpe_ratio=sharpe)


class _OptService:
    def __init__(self):
        self.policies = []

    def _result(self):
        suggestions = [
            SimpleNamespace(symbol="AAA.IS", current_weight=60.0, optimal_weight=40.0),
            SimpleNamespace(symbol="bbb.is", current_weight=40.0, optimal_weight=60.0),
        ]
        return SimpleNamespace(
            current_metrics=_metrics(0.2, 0.3, 0.4), optimized_metrics=_metrics(0.3, 0.28, 0.9),
            min_volatility_metrics=None, suggestions=suggestions,
        )

    def optimize_dashboard_portfolio(self, policy=None):
        self.policies.append(policy)
        return self._result()

    def optimize_model_portfolio(self, pid, policy=None):
        self.policies.append((pid, policy))
        return self._result()

    def _get_historical_prices(self, tickers, days=365):
        rs = np.random.RandomState(1)
        index = pd.date_range("2025-01-01", periods=300, freq="B")
        return pd.DataFrame({t: 100 * np.cumprod(1 + rs.normal(0.0005, 0.01, len(index))) for t in tickers}, index=index)

    def _get_last_price(self, ticker):
        return 12.5 if ticker == "AAA.IS" else None


class _Lookup:
    def get_stocks(self, ids):
        stocks = {1: ("AAA.IS", "AAA Holding.IS"), 2: ("bbb.is", None)}
        return {i: SimpleNamespace(ticker=t, name=n) for i, (t, n) in stocks.items() if i in ids}


def _services(**overrides):
    base = dict(
        opt_service=_OptService(),
        portfolio_service=SimpleNamespace(get_current_portfolio=lambda: SimpleNamespace(active_positions={
            1: SimpleNamespace(total_quantity=10, average_cost=12.0), 2: SimpleNamespace(total_quantity=5, average_cost=None)})),
        model_portfolio_service=SimpleNamespace(get_positions=lambda pid: {1: 10, 2: 5}),
        lookup=_Lookup(),
    )
    base.update(overrides)
    return pipeline.OptimizationServices(**base)


def test_clean_ticker_strips_suffix_and_normalizes_case():
    assert pipeline.clean_ticker(" thyao.is ") == "THYAO"
    assert pipeline.clean_ticker("ASELS.IS") == "ASELS"


def test_build_names_map_registers_raw_clean_and_suffixed_keys():
    stock_map = {1: SimpleNamespace(ticker="aaa.is", name="AAA Holding.IS"), 2: SimpleNamespace(ticker="BBB", name=None)}
    names = pipeline.build_names_map(stock_map, [1, 2, 3])
    assert names["aaa.is"] == names["AAA"] == names["AAA.IS"] == "AAA Holding"
    assert names["BBB"] == names["BBB.IS"] == "BBB"


@pytest.mark.parametrize("override, message", [
    ({"opt_service": None}, "OptimizationService hazır değil."),
    ({"portfolio_service": None}, "PortfolioService bulunamadı."),
    ({"portfolio_service": SimpleNamespace(get_current_portfolio=lambda: SimpleNamespace(active_positions={1: 1}))},
     "Optimizasyon için portföyde en az 2 farklı hisse bulunmalıdır."),
])
def test_dashboard_input_errors(override, message):
    with pytest.raises(pipeline.OptimizationInputError, match=message):
        pipeline.compute_optimization(_services(**override), "dashboard", 0.2, 0.3)


def test_model_input_errors():
    with pytest.raises(pipeline.OptimizationInputError, match="ModelPortfolioService bulunamadı."):
        pipeline.compute_optimization(_services(model_portfolio_service=None), "4", 0.2, 0.3)
    few = SimpleNamespace(get_positions=lambda pid: {1: 3})
    with pytest.raises(pipeline.OptimizationInputError, match="model portföyde en az 2"):
        pipeline.compute_optimization(_services(model_portfolio_service=few), "4", 0.2, 0.3)


def test_compute_dashboard_builds_plan_and_falls_back_to_optimized_min_vol():
    services = _services()
    np.random.seed(0)
    payload = pipeline.compute_optimization(services, "dashboard", 0.2, 0.3)
    policy = services.opt_service.policies[0]
    assert (policy.risk_free_rate, policy.max_single_weight, policy.trading_days_per_year) == (0.3, 0.2, 252)
    assert payload["min_vol_metrics"] is payload["opt_result"].optimized_metrics
    assert len(payload["mc_points"]) == 1000
    assert {row["symbol"] for row in payload["rebalance_plan"]} == {"AAA", "BBB"}


def test_compute_model_portfolio_passes_id_and_policy():
    services = _services()
    np.random.seed(0)
    pipeline.compute_optimization(services, "4", 0.25, 0.1)
    pid, policy = services.opt_service.policies[0]
    assert pid == 4 and policy.max_single_weight == 0.25


def test_frontier_html_embeds_points_and_series():
    html = charts.build_frontier_chart_html(
        mc_points=[{"x": 1.0, "y": 2.0}], frontier_curve=[{"x": 1.5, "y": 2.5}],
        curr_pt={"x": 1.1, "y": 2.2}, opt_pt={"x": 3.3, "y": 4.4}, min_vol_pt={"x": 5.5, "y": 6.6},
    )
    assert "const mcData = [{\"x\": 1.0, \"y\": 2.0}];" in html
    assert "{ x: 3.3, y: 4.4 }" in html and "{ x: 5.5, y: 6.6 }" in html and "{ x: 1.1, y: 2.2 }" in html


def test_weights_html_embeds_labels_and_weights():
    html = charts.build_weights_chart_html([{"symbol": "A", "currentWeight": 10.5, "optimalWeight": 20.25}])
    assert 'labels: ["A"]' in html and "data: [10.5]" in html and "data: [20.25]" in html

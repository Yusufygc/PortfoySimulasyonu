from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.application.services.planning.optimization_market_data import OptimizationPolicy
from src.application.services.planning.optimization_service import OptimizationDeps, OptimizationService


class FakeMarketDataProvider:
    def __init__(self) -> None:
        self.history_requests = []
        self.last_price_requests = []

    def get_historical_prices(self, tickers, days):
        self.history_requests.append((list(tickers), days))
        index = pd.date_range("2026-01-01", periods=80, freq="D")
        return pd.DataFrame(
            {
                tickers[0]: np.linspace(100, 125, len(index)),
                tickers[1]: np.linspace(80, 90, len(index)),
            },
            index=index,
        )

    def get_last_price(self, ticker):
        self.last_price_requests.append(ticker)
        return {"AAA.IS": 125.0, "BBB.IS": 90.0}[ticker]


class ShortHistoryMarketDataProvider(FakeMarketDataProvider):
    def get_historical_prices(self, tickers, days):
        self.history_requests.append((list(tickers), days))
        index = pd.date_range("2026-01-01", periods=10, freq="D")
        return pd.DataFrame({ticker: np.linspace(100, 101, len(index)) for ticker in tickers}, index=index)


class FakePortfolioService:
    def get_current_portfolio(self):
        positions = {
            1: SimpleNamespace(total_quantity=10, average_cost=10.0),
            2: SimpleNamespace(total_quantity=20, average_cost=8.0),
        }
        return SimpleNamespace(positions=positions, active_positions=positions)


class FakeModelPortfolioService:
    def get_all_portfolios(self):
        return []


class FakeStockRepo:
    def get_stocks_by_ids(self, stock_ids):
        tickers = {1: "AAA.IS", 2: "BBB.IS"}
        return [SimpleNamespace(id=stock_id, ticker=tickers[stock_id]) for stock_id in stock_ids]


def _make_service(provider):
    return OptimizationService(
        deps=OptimizationDeps(
            portfolio_service=FakePortfolioService(),
            model_portfolio_service=FakeModelPortfolioService(),
            stock_repo=FakeStockRepo(),
            market_data_provider=provider,
        ),
        policy=OptimizationPolicy(risk_free_rate=0.01, max_single_weight=0.70),
    )


def test_optimization_service_uses_injected_market_data_provider():
    provider = FakeMarketDataProvider()
    service = _make_service(provider)

    result = service.optimize_dashboard_portfolio()

    assert provider.history_requests == [(["AAA.IS", "BBB.IS"], 504)]
    assert provider.last_price_requests == ["AAA.IS", "BBB.IS"]
    assert len(result.suggestions) == 2
    assert result.current_metrics.volatility >= 0
    assert result.optimized_metrics.volatility >= 0


def test_min_volatility_point_has_lowest_or_equal_volatility_of_the_three():
    # Verimli Sınır grafiğinin 3. noktası (bkz. plan §7.3 madde 5, OptimizationView) —
    # minimum volatilite portföyü tanım olarak diğer iki noktadan (mevcut/max-Sharpe)
    # daha düşük veya en fazla eşit volatiliteye sahip olmalıdır.
    provider = FakeMarketDataProvider()
    service = _make_service(provider)

    result = service.optimize_dashboard_portfolio()

    assert result.min_volatility_metrics is not None
    epsilon = 1e-6
    assert result.min_volatility_metrics.volatility <= result.optimized_metrics.volatility + epsilon
    assert result.min_volatility_metrics.volatility <= result.current_metrics.volatility + epsilon


def test_optimization_rejects_short_history():
    service = _make_service(ShortHistoryMarketDataProvider())

    with pytest.raises(ValueError, match="Yeterli fiyat gecmisi"):
        service.optimize_dashboard_portfolio()


def test_optimization_raises_when_slsqp_fails(monkeypatch):
    service = _make_service(FakeMarketDataProvider())

    monkeypatch.setattr(
        "src.application.services.planning.optimization_service.minimize",
        lambda *args, **kwargs: SimpleNamespace(success=False),
    )

    with pytest.raises(ValueError, match="Optimizasyon hesaplanamadi"):
        service.optimize_dashboard_portfolio()


def test_optimization_metrics_guard_zero_volatility():
    service = _make_service(FakeMarketDataProvider())

    metrics = service._calculate_metrics(
        weights=np.array([0.5, 0.5]),
        mean_returns=np.array([0.10, 0.20]),
        cov_matrix=np.zeros((2, 2)),
    )

    assert metrics.expected_return == pytest.approx(0.15)
    assert metrics.volatility == 0.0
    assert metrics.sharpe_ratio == 0.0


class PartialMarketDataProvider(FakeMarketDataProvider):
    def get_historical_prices(self, tickers, days):
        self.history_requests.append((list(tickers), days))
        index = pd.date_range("2026-01-01", periods=80, freq="D")
        valid_tickers = [t for t in tickers if t != "CCC.IS"]
        return pd.DataFrame(
            {t: np.linspace(100, 110, len(index)) for t in valid_tickers},
            index=index,
        )

    def get_last_price(self, ticker):
        self.last_price_requests.append(ticker)
        return {"AAA.IS": 100.0, "BBB.IS": 110.0, "CCC.IS": 50.0}[ticker]


class FakeThreeStockRepo:
    def get_stocks_by_ids(self, stock_ids):
        tickers = {1: "AAA.IS", 2: "BBB.IS", 3: "CCC.IS"}
        return [SimpleNamespace(id=stock_id, ticker=tickers[stock_id]) for stock_id in stock_ids]


class FakeThreeStockPortfolioService:
    def get_current_portfolio(self):
        positions = {
            1: SimpleNamespace(total_quantity=10, average_cost=100.0), # AAA.IS: value 10 * 100 = 1000
            2: SimpleNamespace(total_quantity=10, average_cost=110.0), # BBB.IS: value 10 * 110 = 1100
            3: SimpleNamespace(total_quantity=10, average_cost=50.0),  # CCC.IS: value 10 * 50 = 500 (Invalid/Insufficient)
        }
        return SimpleNamespace(positions=positions, active_positions=positions)


def test_optimization_graceful_handling_invalid_tickers():
    provider = PartialMarketDataProvider()
    service = OptimizationService(
        deps=OptimizationDeps(
            portfolio_service=FakeThreeStockPortfolioService(),
            model_portfolio_service=FakeModelPortfolioService(),
            stock_repo=FakeThreeStockRepo(),
            market_data_provider=provider,
        ),
        policy=OptimizationPolicy(risk_free_rate=0.01, max_single_weight=0.70),
    )

    result = service.optimize_dashboard_portfolio()

    # CCC.IS should be treated as invalid and set as TUT
    # Check suggestions list
    sug_map = {s.symbol: s for s in result.suggestions}
    assert "CCC.IS" in sug_map
    assert sug_map["CCC.IS"].action == "TUT"
    assert sug_map["CCC.IS"].optimal_weight == sug_map["CCC.IS"].current_weight
    assert sug_map["CCC.IS"].change == 0.0

    # AAA.IS and BBB.IS should be optimized and their optimal weights + CCC.IS current weight should sum to 100%
    total_opt_w = sum(s.optimal_weight for s in result.suggestions)
    assert total_opt_w == pytest.approx(100.0)


class TestPerCallPolicyOverride:
    """Bkz. RiskOptimizationBridgeService (§5.3): DI singleton'ın politikasını değiştirmeden
    tek çağrılık kısıt uygulanabilmeli."""

    def test_calculate_metrics_accepts_risk_free_rate_override(self):
        service = _make_service(FakeMarketDataProvider())  # policy.risk_free_rate=0.01
        weights = np.array([0.5, 0.5])
        mean_returns = np.array([0.10, 0.20])
        cov_matrix = np.array([[0.04, 0.0], [0.0, 0.04]])

        default_metrics = service._calculate_metrics(weights, mean_returns, cov_matrix)
        overridden_metrics = service._calculate_metrics(weights, mean_returns, cov_matrix, risk_free_rate=0.20)

        assert overridden_metrics.expected_return == default_metrics.expected_return
        assert overridden_metrics.sharpe_ratio < default_metrics.sharpe_ratio

    def test_optimize_dashboard_portfolio_accepts_per_call_policy_without_mutating_default(self):
        service = _make_service(FakeMarketDataProvider())
        original_max_weight = service.policy.max_single_weight

        override_policy = OptimizationPolicy(risk_free_rate=0.05, max_single_weight=0.05)
        result = service.optimize_dashboard_portfolio(policy=override_policy)

        assert len(result.suggestions) == 2
        assert service.policy.max_single_weight == original_max_weight

    def test_optimize_model_portfolio_accepts_per_call_policy_without_mutating_default(self, monkeypatch):
        service = _make_service(FakeMarketDataProvider())
        monkeypatch.setattr(
            service, "_model_portfolio_service", SimpleNamespace(get_positions=lambda pid: {1: 10, 2: 20}),
        )
        original_max_weight = service.policy.max_single_weight

        result = service.optimize_model_portfolio(
            portfolio_id=1, policy=OptimizationPolicy(max_single_weight=0.15),
        )

        assert len(result.suggestions) == 2
        assert service.policy.max_single_weight == original_max_weight


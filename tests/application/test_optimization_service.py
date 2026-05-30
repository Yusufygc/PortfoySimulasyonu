from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd

from src.application.services.planning.optimization_market_data import OptimizationPolicy
from src.application.services.planning.optimization_service import OptimizationService


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


def test_optimization_service_uses_injected_market_data_provider():
    provider = FakeMarketDataProvider()
    service = OptimizationService(
        portfolio_service=FakePortfolioService(),
        model_portfolio_service=FakeModelPortfolioService(),
        stock_repo=FakeStockRepo(),
        market_data_provider=provider,
        policy=OptimizationPolicy(risk_free_rate=0.01, max_single_weight=0.70),
    )

    result = service.optimize_dashboard_portfolio()

    assert provider.history_requests == [(["AAA.IS", "BBB.IS"], 504)]
    assert provider.last_price_requests == ["AAA.IS", "BBB.IS"]
    assert len(result.suggestions) == 2
    assert result.current_metrics.volatility >= 0
    assert result.optimized_metrics.volatility >= 0

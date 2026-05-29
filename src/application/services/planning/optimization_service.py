from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf

from src.application.services.planning.optimization_market_data import (
    OptimizationMarketDataProvider,
    OptimizationPolicy,
    YFinanceOptimizationMarketDataProvider,
)
from src.domain.models.optimization_result import (
    OptimizationMetrics,
    OptimizationResult,
    OptimizationSuggestion,
)


class OptimizationService:
    TRADING_DAYS_PER_YEAR = 252
    DEFAULT_RISK_FREE_RATE = 0.30
    MAX_SINGLE_WEIGHT = 0.40

    def __init__(
        self,
        portfolio_service,
        model_portfolio_service,
        stock_repo,
        risk_free_rate: float | None = None,
        market_data_provider: OptimizationMarketDataProvider | None = None,
        policy: OptimizationPolicy | None = None,
    ) -> None:
        self._portfolio_service = portfolio_service
        self._model_portfolio_service = model_portfolio_service
        self._stock_repo = stock_repo

        base_policy = policy or OptimizationPolicy()
        if risk_free_rate is not None:
            base_policy = OptimizationPolicy(
                trading_days_per_year=base_policy.trading_days_per_year,
                risk_free_rate=risk_free_rate,
                max_single_weight=base_policy.max_single_weight,
            )
        self._policy = base_policy
        self._risk_free_rate = base_policy.risk_free_rate
        self._market_data_provider = market_data_provider or YFinanceOptimizationMarketDataProvider()

    def optimize_dashboard_portfolio(self) -> OptimizationResult:
        portfolio = self._portfolio_service.get_current_portfolio()
        positions = portfolio.active_positions

        if len(positions) < 2:
            raise ValueError("Optimizasyon icin portfoyde en az 2 farkli hisse olmalidir.")

        stock_ids = list(positions.keys())
        stocks = self._stock_repo.get_stocks_by_ids(stock_ids)
        stock_map = {s.id: s for s in stocks}
        tickers = [stock_map[sid].ticker for sid in stock_ids]
        current_weights = self._calculate_weights_from_positions(positions, tickers)

        return self._optimize(tickers, current_weights)

    def optimize_model_portfolio(
        self,
        portfolio_id: int,
        price_lookup_func=None,
    ) -> OptimizationResult:
        positions = self._model_portfolio_service.get_positions(portfolio_id)

        if len(positions) < 2:
            raise ValueError("Optimizasyon icin portfoyde en az 2 farkli hisse olmalidir.")

        stock_ids = list(positions.keys())
        stocks = self._stock_repo.get_stocks_by_ids(stock_ids)
        stock_map = {s.id: s for s in stocks}

        tickers = [stock_map[sid].ticker for sid in stock_ids]
        quantities = [positions[sid] for sid in stock_ids]
        current_weights = self._calculate_weights_with_prices(tickers, quantities, price_lookup_func)

        return self._optimize(tickers, current_weights)

    def get_model_portfolios(self) -> list:
        return self._model_portfolio_service.get_all_portfolios()

    def _optimize(
        self,
        tickers: List[str],
        current_weights: np.ndarray,
    ) -> OptimizationResult:
        price_df = self._get_historical_prices(tickers, days=504)
        if price_df.empty or len(price_df) < 60:
            raise ValueError("Yeterli fiyat gecmisi bulunamadi (en az 60 gun gerekli).")

        log_returns = np.log(price_df / price_df.shift(1)).dropna()
        mean_returns = log_returns.mean() * self._policy.trading_days_per_year

        lw = LedoitWolf()
        lw.fit(log_returns.values)
        cov_matrix = pd.DataFrame(
            lw.covariance_ * self._policy.trading_days_per_year,
            index=log_returns.columns,
            columns=log_returns.columns,
        )

        num_assets = len(tickers)
        initial_weights = np.array([1.0 / num_assets] * num_assets)
        constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1}
        max_w = max(self._policy.max_single_weight, 1.0 / num_assets)
        bounds = tuple((0.0, max_w) for _ in range(num_assets))

        result = minimize(
            self._negative_sharpe_ratio,
            initial_weights,
            args=(mean_returns.values, cov_matrix.values, self._risk_free_rate),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        if not result.success:
            raise ValueError("Optimizasyon hesaplanamadi. Lutfen tekrar deneyin.")

        optimal_weights = result.x
        current_metrics = self._calculate_metrics(current_weights, mean_returns.values, cov_matrix.values)
        optimized_metrics = self._calculate_metrics(optimal_weights, mean_returns.values, cov_matrix.values)
        suggestions = self._build_suggestions(tickers, current_weights, optimal_weights)

        return OptimizationResult(
            current_metrics=current_metrics,
            optimized_metrics=optimized_metrics,
            suggestions=suggestions,
        )

    @staticmethod
    def _negative_sharpe_ratio(
        weights: np.ndarray,
        mean_returns: np.ndarray,
        cov_matrix: np.ndarray,
        risk_free_rate: float,
    ) -> float:
        portfolio_return = np.sum(mean_returns * weights)
        portfolio_volatility = np.sqrt(weights.T @ cov_matrix @ weights)
        return -(portfolio_return - risk_free_rate) / portfolio_volatility

    def _calculate_metrics(
        self,
        weights: np.ndarray,
        mean_returns: np.ndarray,
        cov_matrix: np.ndarray,
    ) -> OptimizationMetrics:
        portfolio_return = float(np.sum(mean_returns * weights))
        portfolio_volatility = float(np.sqrt(weights.T @ cov_matrix @ weights))
        sharpe = (portfolio_return - self._risk_free_rate) / portfolio_volatility

        return OptimizationMetrics(
            expected_return=portfolio_return,
            volatility=portfolio_volatility,
            sharpe_ratio=float(sharpe),
        )

    @staticmethod
    def _build_suggestions(
        tickers: List[str],
        current_weights: np.ndarray,
        optimal_weights: np.ndarray,
    ) -> List[OptimizationSuggestion]:
        suggestions = []
        for i, ticker in enumerate(tickers):
            curr_w = current_weights[i] * 100
            opt_w = optimal_weights[i] * 100
            diff = opt_w - curr_w

            if diff > 1.0:
                action = "EKLE"
            elif diff < -1.0:
                action = "AZALT"
            else:
                action = "TUT"

            suggestions.append(
                OptimizationSuggestion(
                    symbol=ticker,
                    current_weight=curr_w,
                    optimal_weight=opt_w,
                    change=diff,
                    action=action,
                )
            )

        suggestions.sort(key=lambda s: s.optimal_weight, reverse=True)
        return suggestions

    def _get_historical_prices(self, tickers: List[str], days: int = 365) -> pd.DataFrame:
        return self._market_data_provider.get_historical_prices(tickers, days)

    def _calculate_weights_from_positions(
        self,
        positions: dict,
        tickers: List[str],
    ) -> np.ndarray:
        values = []
        for ticker, (stock_id, position) in zip(tickers, positions.items()):
            price = self._get_last_price(ticker)
            if price is None and position.average_cost is not None:
                price = float(position.average_cost)
            elif price is None:
                price = 1.0
            values.append(position.total_quantity * price)

        total = sum(values)
        if total == 0:
            n = len(values)
            return np.array([1.0 / n] * n)

        return np.array([v / total for v in values])

    def _calculate_weights_with_prices(
        self,
        tickers: List[str],
        quantities: List[int],
        price_lookup_func=None,
    ) -> np.ndarray:
        values = []
        for ticker, qty in zip(tickers, quantities):
            price = None
            if price_lookup_func:
                try:
                    result = price_lookup_func(ticker)
                    if result:
                        price = float(result.price)
                except Exception:
                    pass

            if price is None:
                price = self._get_last_price(ticker) or 1.0

            values.append(qty * price)

        total = sum(values)
        if total == 0:
            n = len(values)
            return np.array([1.0 / n] * n)

        return np.array([v / total for v in values])

    def _get_last_price(self, ticker: str) -> Optional[float]:
        return self._market_data_provider.get_last_price(ticker)

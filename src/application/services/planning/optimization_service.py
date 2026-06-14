from __future__ import annotations

from typing import List, NamedTuple, Optional

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf

from src.application.services.planning.optimization_market_data import (
    OptimizationMarketDataProvider,
    OptimizationPolicy,
)
from src.domain.models.optimization_result import (
    OptimizationMetrics,
    OptimizationResult,
    OptimizationSuggestion,
)


def _split_tickers_by_price_history(
    price_df: pd.DataFrame,
    tickers: List[str],
) -> tuple[list[str], list[str]]:
    valid_tickers = list(price_df.columns) if not price_df.empty else []
    invalid_tickers = [ticker for ticker in tickers if ticker not in valid_tickers]
    return valid_tickers, invalid_tickers


def _ensure_optimizable_history(
    price_df: pd.DataFrame,
    valid_tickers: list[str],
    invalid_tickers: list[str],
) -> None:
    if len(valid_tickers) >= 2 and not price_df.empty and len(price_df) >= 60:
        return

    if invalid_tickers:
        raise ValueError(
            "Optimizasyon icin yeterli fiyat gecmisi olan en az 2 hisse bulunmalidir.\n"
            f"Gecersiz veya yetersiz verisi olan hisseler: {', '.join(invalid_tickers)}"
        )
    raise ValueError("Yeterli fiyat gecmisi bulunamadi (en az 60 gun gerekli).")


def _build_return_model(
    price_df: pd.DataFrame,
    trading_days_per_year: int,
) -> tuple[pd.Series, pd.DataFrame]:
    log_returns = np.log(price_df / price_df.shift(1)).replace([np.inf, -np.inf], np.nan).dropna()
    if log_returns.empty or len(log_returns) < 2:
        raise ValueError("Yeterli fiyat gecmisi bulunamadi (en az 60 gun gerekli).")

    mean_returns = log_returns.mean() * trading_days_per_year
    estimator = LedoitWolf()
    estimator.fit(log_returns.values)
    cov_matrix = pd.DataFrame(
        estimator.covariance_ * trading_days_per_year,
        index=log_returns.columns,
        columns=log_returns.columns,
    )
    return mean_returns, cov_matrix


def _portfolio_volatility(weights: np.ndarray, cov_matrix: np.ndarray) -> float:
    variance = float(weights.T @ cov_matrix @ weights)
    if variance <= 0 or not np.isfinite(variance):
        return 0.0
    return float(np.sqrt(variance))


def _negative_sharpe_ratio(
    weights: np.ndarray,
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
    risk_free_rate: float,
) -> float:
    portfolio_return = np.sum(mean_returns * weights)
    portfolio_volatility = _portfolio_volatility(weights, cov_matrix)
    if portfolio_volatility <= 0 or not np.isfinite(portfolio_volatility):
        return 1e9
    return -(portfolio_return - risk_free_rate) / portfolio_volatility


def _optimize_valid_weights(
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
    risk_free_rate: float,
    max_single_weight: float,
    remaining_weight: float,
) -> np.ndarray:
    num_assets = len(mean_returns)
    initial_weights = np.array([1.0 / num_assets] * num_assets)
    constraints = {"type": "eq", "fun": lambda weights: np.sum(weights) - 1}
    max_weight = max(max_single_weight, 1.0 / num_assets)
    bounds = tuple((0.0, max_weight) for _ in range(num_assets))

    result = minimize(
        _negative_sharpe_ratio,
        initial_weights,
        args=(mean_returns, cov_matrix, risk_free_rate),
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
    )

    if not result.success:
        raise ValueError("Optimizasyon hesaplanamadi. Lutfen tekrar deneyin.")

    return result.x * remaining_weight


def _suggestion_action(weight_diff: float) -> str:
    if weight_diff > 1.0:
        return "EKLE"
    if weight_diff < -1.0:
        return "AZALT"
    return "TUT"


def _build_partial_suggestions(
    tickers: List[str],
    valid_tickers: list[str],
    invalid_tickers: list[str],
    current_weights: np.ndarray,
    optimal_valid_weights: np.ndarray,
) -> list[OptimizationSuggestion]:
    suggestions = []
    for index, ticker in enumerate(valid_tickers):
        current_weight = current_weights[tickers.index(ticker)] * 100
        optimal_weight = optimal_valid_weights[index] * 100
        change = optimal_weight - current_weight
        suggestions.append(
            OptimizationSuggestion(
                symbol=ticker,
                current_weight=current_weight,
                optimal_weight=optimal_weight,
                change=change,
                action=_suggestion_action(change),
            )
        )

    for ticker in invalid_tickers:
        current_weight = current_weights[tickers.index(ticker)] * 100
        suggestions.append(
            OptimizationSuggestion(
                symbol=ticker,
                current_weight=current_weight,
                optimal_weight=current_weight,
                change=0.0,
                action="TUT",
            )
        )

    suggestions.sort(key=lambda item: item.optimal_weight, reverse=True)
    return suggestions


class OptimizationDeps(NamedTuple):
    portfolio_service: object
    model_portfolio_service: object
    stock_repo: object
    market_data_provider: OptimizationMarketDataProvider


class OptimizationService:
    TRADING_DAYS_PER_YEAR = 252
    DEFAULT_RISK_FREE_RATE = 0.30
    MAX_SINGLE_WEIGHT = 0.40

    def __init__(
        self,
        deps: OptimizationDeps,
        risk_free_rate: float | None = None,
        policy: OptimizationPolicy | None = None,
    ) -> None:
        self._portfolio_service = deps.portfolio_service
        self._model_portfolio_service = deps.model_portfolio_service
        self._stock_repo = deps.stock_repo

        base_policy = policy or OptimizationPolicy()
        if risk_free_rate is not None:
            base_policy = OptimizationPolicy(
                trading_days_per_year=base_policy.trading_days_per_year,
                risk_free_rate=risk_free_rate,
                max_single_weight=base_policy.max_single_weight,
            )
        self._policy = base_policy
        self._risk_free_rate = base_policy.risk_free_rate
        self._market_data_provider = deps.market_data_provider

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
        valid_tickers, invalid_tickers = _split_tickers_by_price_history(price_df, tickers)
        _ensure_optimizable_history(price_df, valid_tickers, invalid_tickers)

        mean_returns, cov_matrix = _build_return_model(price_df, self._policy.trading_days_per_year)

        invalid_indices = [tickers.index(t) for t in invalid_tickers]
        invalid_sum = float(np.sum(current_weights[invalid_indices])) if invalid_tickers else 0.0
        remaining_weight = max(0.0, 1.0 - invalid_sum)
        optimal_weights_scaled = _optimize_valid_weights(
            mean_returns.values,
            cov_matrix.values,
            self._risk_free_rate,
            self._policy.max_single_weight,
            remaining_weight,
        )

        valid_indices = [tickers.index(t) for t in valid_tickers]
        current_valid_weights = current_weights[valid_indices]
        
        current_metrics = self._calculate_metrics(current_valid_weights, mean_returns.values, cov_matrix.values)
        optimized_metrics = self._calculate_metrics(optimal_weights_scaled, mean_returns.values, cov_matrix.values)
        suggestions = _build_partial_suggestions(
            tickers,
            valid_tickers,
            invalid_tickers,
            current_weights,
            optimal_weights_scaled,
        )

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
        return _negative_sharpe_ratio(weights, mean_returns, cov_matrix, risk_free_rate)

    def _calculate_metrics(
        self,
        weights: np.ndarray,
        mean_returns: np.ndarray,
        cov_matrix: np.ndarray,
    ) -> OptimizationMetrics:
        portfolio_return = float(np.sum(mean_returns * weights))
        if not np.isfinite(portfolio_return):
            portfolio_return = 0.0

        portfolio_volatility = self._portfolio_volatility(weights, cov_matrix)
        if portfolio_volatility <= 0 or not np.isfinite(portfolio_volatility):
            portfolio_volatility = 0.0
            sharpe = 0.0
        else:
            sharpe = (portfolio_return - self._risk_free_rate) / portfolio_volatility
            if not np.isfinite(sharpe):
                sharpe = 0.0

        return OptimizationMetrics(
            expected_return=portfolio_return,
            volatility=portfolio_volatility,
            sharpe_ratio=float(sharpe),
        )

    @staticmethod
    def _portfolio_volatility(weights: np.ndarray, cov_matrix: np.ndarray) -> float:
        return _portfolio_volatility(weights, cov_matrix)

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

            suggestions.append(
                OptimizationSuggestion(
                    symbol=ticker,
                    current_weight=curr_w,
                    optimal_weight=opt_w,
                    change=diff,
                    action=_suggestion_action(diff),
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

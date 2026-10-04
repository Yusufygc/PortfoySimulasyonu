"""Optimizasyon sayfası hesap hattı: pozisyonlar, Markowitz sonucu, Monte Carlo, verimli sınır ve rebalance planı.

Arka plan iş parçacığında çalışır; denetleyici durumundan bağımsızdır, yalnızca verilen servislerle çalışır.
Girdi sorunları (eksik servis, yetersiz pozisyon) `OptimizationInputError` ile bildirilir.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from src.application.services.planning.frontier_simulation import (
    calculate_efficient_frontier_curve,
    calculate_rebalance_plan,
    simulate_monte_carlo,
)
from src.application.services.planning.optimization_market_data import OptimizationPolicy
from src.application.services.planning.optimization_service import _build_return_model

_MIN_POSITIONS = 2
_TRADING_DAYS = 252


class OptimizationInputError(Exception):
    """Kullanıcıya olduğu gibi gösterilecek girdi/servis hatası."""


@dataclass
class OptimizationServices:
    opt_service: Any
    portfolio_service: Any
    model_portfolio_service: Any
    lookup: Any


def clean_ticker(raw: str) -> str:
    return raw.replace(".IS", "").replace(".is", "").strip().upper()


def _load_dashboard(services: OptimizationServices, policy: OptimizationPolicy) -> Tuple[Dict[int, Any], float, Any]:
    if not services.portfolio_service:
        raise OptimizationInputError("PortfolioService bulunamadı.")
    positions = services.portfolio_service.get_current_portfolio().active_positions
    if len(positions) < _MIN_POSITIONS:
        raise OptimizationInputError("Optimizasyon için portföyde en az 2 farklı hisse bulunmalıdır.")
    # Toplam piyasa değeri
    total_val = sum(pos.total_quantity * float(pos.average_cost or 1.0) for pos in positions.values())
    return positions, total_val, services.opt_service.optimize_dashboard_portfolio(policy=policy)


def _load_model(services: OptimizationServices, portfolio_code: str, policy: OptimizationPolicy) -> Tuple[Dict[int, Any], float, Any]:
    if not services.model_portfolio_service:
        raise OptimizationInputError("ModelPortfolioService bulunamadı.")
    pid = int(portfolio_code)
    positions = services.model_portfolio_service.get_positions(pid)
    if len(positions) < _MIN_POSITIONS:
        raise OptimizationInputError("Optimizasyon için model portföyde en az 2 farklı hisse bulunmalıdır.")
    total_val = sum(qty * 100.0 for qty in positions.values())  # Yaklaşık baz değer
    return positions, total_val, services.opt_service.optimize_model_portfolio(pid, policy=policy)


def build_names_map(stock_map: Dict[int, Any], stock_ids: List[int]) -> Dict[str, str]:
    """Ham, temiz ve `.IS` sonekli ticker anahtarlarından görüntü adına eşleme."""
    names_map: Dict[str, str] = {}
    for sid in stock_ids:
        if sid not in stock_map:
            continue
        stk = stock_map[sid]
        raw_tick = stk.ticker
        clean_tick = clean_ticker(raw_tick)
        raw_name = getattr(stk, "name", None)
        if raw_name:
            clean_n = raw_name.replace(".IS", "").replace(".is", "").strip()
            display_name = clean_n if clean_n and clean_n.upper() != f"{clean_tick}.IS" else clean_tick
        else:
            display_name = clean_tick
        names_map[raw_tick] = display_name
        names_map[clean_tick] = display_name
        names_map[f"{clean_tick}.IS"] = display_name
    return names_map


def _last_prices(opt_service: Any, tickers: List[str]) -> Dict[str, float]:
    last_prices: Dict[str, float] = {}
    for t in tickers:
        p = opt_service._get_last_price(t)
        val = float(p) if p else 1.0
        last_prices[t] = val
        last_prices[clean_ticker(t)] = val
    return last_prices


def _rebalance_plan(opt_result: Any, total_val: float, last_prices: Dict[str, float], names_map: Dict[str, str]) -> list:
    curr_w_map = {clean_ticker(s.symbol): s.current_weight for s in opt_result.suggestions}
    opt_w_map = {clean_ticker(s.symbol): s.optimal_weight for s in opt_result.suggestions}
    return calculate_rebalance_plan(
        total_portfolio_value=total_val if total_val > 0 else 100000.0,
        current_weights=curr_w_map,
        optimal_weights=opt_w_map,
        last_prices=last_prices,
        stock_names=names_map,
    )


def compute_optimization(
    services: OptimizationServices,
    portfolio_code: str,
    max_single_weight: float,
    risk_free_rate: float,
) -> Dict[str, Optional[Any]]:
    """Optimizasyonu, Monte Carlo simülasyonunu, verimli sınırı ve rebalance planını hesaplar."""
    if not services.opt_service:
        raise OptimizationInputError("OptimizationService hazır değil.")

    policy = OptimizationPolicy(
        trading_days_per_year=_TRADING_DAYS,
        risk_free_rate=risk_free_rate,
        max_single_weight=max_single_weight,
    )

    # 1. Hisseleri ve Pozisyonları Çek
    if portfolio_code == "dashboard":
        positions, total_val, opt_result = _load_dashboard(services, policy)
    else:
        positions, total_val, opt_result = _load_model(services, portfolio_code, policy)

    # 2. Hisse Sembolleri ve İsimlerini Al
    stock_ids = list(positions.keys())
    stock_map = services.lookup.get_stocks(stock_ids) if services.lookup else {}
    tickers = [stock_map[sid].ticker for sid in stock_ids if sid in stock_map]
    names_map = build_names_map(stock_map, stock_ids)

    # 3. Fiyat Geçmişi ve Kovaryans Matrisi
    price_df = services.opt_service._get_historical_prices(tickers, days=504)
    mean_returns, cov_matrix = _build_return_model(price_df, trading_days_per_year=_TRADING_DAYS)

    # 4. Monte Carlo Simülasyonu (1.000 Nokta)
    mc_points = simulate_monte_carlo(
        mean_returns.values, cov_matrix.values, risk_free_rate=risk_free_rate, num_simulations=1000
    )

    # 5. Efficient Frontier Eğrisi (20 Nokta)
    frontier_curve = calculate_efficient_frontier_curve(
        mean_returns.values, cov_matrix.values, max_single_weight=max_single_weight, points_count=20
    )

    # 6. Rebalance Planı ve Son Fiyatlar
    last_prices = _last_prices(services.opt_service, tickers)
    rebalance_plan = _rebalance_plan(opt_result, total_val, last_prices, names_map)

    return {
        "opt_result": opt_result,
        "mc_points": mc_points,
        "frontier_curve": frontier_curve,
        "rebalance_plan": rebalance_plan,
        "min_vol_metrics": opt_result.min_volatility_metrics or opt_result.optimized_metrics,
    }

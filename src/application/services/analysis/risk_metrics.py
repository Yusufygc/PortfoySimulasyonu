from __future__ import annotations

import math
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

from src.domain.models.portfolio import Portfolio


def compute_return_pct(series: Dict[date, Decimal]) -> Optional[float]:
    if not series:
        return None
    values = [value for value in series.values() if value is not None]
    start = next((value for value in values if value > 0), None)
    end = values[-1] if values else None
    if start is None or end is None or start == 0:
        return None
    return float(((end - start) / start) * Decimal("100"))


def compute_relative_gap_pct(
    portfolio_series: Dict[date, Decimal],
    benchmark_series: Dict[date, Decimal],
) -> Optional[float]:
    portfolio_return = compute_return_pct(portfolio_series)
    benchmark_return = compute_return_pct(benchmark_series)
    if portfolio_return is None or benchmark_return is None:
        return None
    return portfolio_return - benchmark_return


def compute_daily_return_vector(series: Dict[date, Decimal]) -> List[float]:
    dates = sorted(series.keys())
    returns: List[float] = []
    for prev_date, curr_date in zip(dates, dates[1:]):
        if curr_date.weekday() >= 5:
            continue
        prev_val = float(series[prev_date] or 0)
        curr_val = float(series[curr_date] or 0)
        if prev_val > 0:
            returns.append((curr_val - prev_val) / prev_val)
    return returns


def compute_volatility_pct(series: Dict[date, Decimal]) -> Optional[float]:
    returns = compute_daily_return_vector(series)
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((item - mean) ** 2 for item in returns) / (len(returns) - 1)
    return math.sqrt(variance) * math.sqrt(252) * 100

def compute_sharpe_ratio(series: Dict[date, Decimal], risk_free_rate: float = 0.40) -> Optional[float]:
    returns = compute_daily_return_vector(series)
    if len(returns) < 2:
        return None
    daily_rf = risk_free_rate / 252.0
    excess_returns = [r - daily_rf for r in returns]
    mean_excess = sum(excess_returns) / len(excess_returns)
    variance = sum((r - (sum(returns)/len(returns))) ** 2 for r in returns) / (len(returns) - 1)
    if variance == 0:
        return None
    return (mean_excess / math.sqrt(variance)) * math.sqrt(252)

def compute_beta(portfolio_series: Dict[date, Decimal], benchmark_series: Dict[date, Decimal]) -> Optional[float]:
    dates = sorted(set(portfolio_series.keys()) & set(benchmark_series.keys()))
    port_returns = []
    bench_returns = []
    for prev_date, curr_date in zip(dates, dates[1:]):
        if curr_date.weekday() >= 5:
            continue
        p_prev, p_curr = float(portfolio_series[prev_date] or 0), float(portfolio_series[curr_date] or 0)
        b_prev, b_curr = float(benchmark_series[prev_date] or 0), float(benchmark_series[curr_date] or 0)
        if p_prev > 0 and b_prev > 0:
            port_returns.append((p_curr - p_prev) / p_prev)
            bench_returns.append((b_curr - b_prev) / b_prev)
    if len(port_returns) < 2:
        return None
    p_mean = sum(port_returns) / len(port_returns)
    b_mean = sum(bench_returns) / len(bench_returns)
    covariance = sum((p - p_mean) * (b - b_mean) for p, b in zip(port_returns, bench_returns)) / (len(port_returns) - 1)
    b_variance = sum((b - b_mean) ** 2 for b in bench_returns) / (len(bench_returns) - 1)
    if b_variance == 0:
        return None
    return covariance / b_variance

def compute_alpha(portfolio_series: Dict[date, Decimal], benchmark_series: Dict[date, Decimal], risk_free_rate: float = 0.40) -> Optional[float]:
    beta = compute_beta(portfolio_series, benchmark_series)
    if beta is None:
        return None
    p_return = compute_return_pct(portfolio_series)
    b_return = compute_return_pct(benchmark_series)
    if p_return is None or b_return is None:
        return None
    dates = sorted(portfolio_series.keys())
    if not dates: return None
    days = (dates[-1] - dates[0]).days
    if days == 0: return None
    period_rf = risk_free_rate * (days / 365.0) * 100.0
    return p_return - (period_rf + beta * (b_return - period_rf))


def compute_max_drawdown_pct(series: Dict[date, Decimal]) -> Optional[float]:
    values = [float(value) for value in series.values() if value is not None and value > 0]
    if not values:
        return None
    peak = values[0]
    max_drawdown = 0.0
    for value in values:
        peak = max(peak, value)
        if peak == 0:
            continue
        drawdown = ((value - peak) / peak) * 100
        max_drawdown = min(max_drawdown, drawdown)
    return max_drawdown


def get_concentration_label(top_three_weight_pct: Optional[float]) -> str:
    if top_three_weight_pct is None:
        return "Veri Yok"
    if top_three_weight_pct >= 75:
        return "Yuksek"
    if top_three_weight_pct >= 50:
        return "Orta"
    return "Dusuk"


def build_benchmark_insight(benchmark_label: str, gap: Optional[float]) -> str:
    if gap is None:
        return f"{benchmark_label} kiyasi icin yeterli veri yok."
    if gap >= 0:
        return f"Portfoy {benchmark_label} kiyasinin %{gap:.2f} uzerinde."
    return f"Portfoy {benchmark_label} kiyasinin %{abs(gap):.2f} gerisinde."


def compute_position_snapshot(
    portfolio: Portfolio,
    ticker_map: Dict[int, str],
    current_values: Dict[int, Decimal] | None = None,
) -> List[Dict[str, object]]:
    values_by_stock = current_values or {}
    total_value = sum(
        (
            values_by_stock.get(stock_id, Decimal("0"))
            for stock_id, position in portfolio.positions.items()
            if position.total_quantity > 0
        ),
        Decimal("0"),
    )
    items: List[Dict[str, object]] = []
    for stock_id, position in portfolio.positions.items():
        if position.total_quantity <= 0:
            continue
        current_value = values_by_stock.get(stock_id, Decimal("0"))
        weight = float((current_value / total_value) * Decimal("100")) if total_value > 0 else 0.0
        return_pct = None
        if position.total_cost > 0:
            return_pct = float(((current_value - position.total_cost) / position.total_cost) * Decimal("100"))
        items.append(
            {
                "label": ticker_map.get(stock_id, str(stock_id)),
                "current_value": current_value,
                "cost_value": position.total_cost,
                "weight": weight,
                "return_pct": return_pct if return_pct is not None else 0.0,
            }
        )
    return items

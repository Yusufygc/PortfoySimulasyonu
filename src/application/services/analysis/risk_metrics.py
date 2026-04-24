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
    values = [float(value) for value in series.values() if value is not None and value > 0]
    returns: List[float] = []
    for prev, curr in zip(values, values[1:]):
        if prev == 0:
            continue
        returns.append((curr - prev) / prev)
    return returns


def compute_volatility_pct(series: Dict[date, Decimal]) -> Optional[float]:
    returns = compute_daily_return_vector(series)
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((item - mean) ** 2 for item in returns) / (len(returns) - 1)
    return math.sqrt(variance) * math.sqrt(252) * 100


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
) -> List[Dict[str, object]]:
    total_value = sum(
        (
            getattr(position, "_analysis_current_value", Decimal("0"))
            for position in portfolio.positions.values()
            if position.total_quantity > 0
        ),
        Decimal("0"),
    )
    items: List[Dict[str, object]] = []
    for stock_id, position in portfolio.positions.items():
        if position.total_quantity <= 0:
            continue
        current_value = getattr(position, "_analysis_current_value", Decimal("0"))
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


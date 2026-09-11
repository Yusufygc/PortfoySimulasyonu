from __future__ import annotations

import math
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

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

def _safe_float_0(v) -> float:
    return float(v or 0)


def compute_beta(portfolio_series: Dict[date, Decimal], benchmark_series: Dict[date, Decimal]) -> Optional[float]:
    dates = sorted(set(portfolio_series.keys()) & set(benchmark_series.keys()))
    port_returns = []
    bench_returns = []
    for prev_date, curr_date in zip(dates, dates[1:]):
        if curr_date.weekday() >= 5:
            continue
        p_prev = _safe_float_0(portfolio_series[prev_date])
        p_curr = _safe_float_0(portfolio_series[curr_date])
        b_prev = _safe_float_0(benchmark_series[prev_date])
        b_curr = _safe_float_0(benchmark_series[curr_date])
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


def compute_sortino_ratio(series: Dict[date, Decimal], risk_free_rate: float = 0.40) -> Optional[float]:
    """Sortino Ratio — Sharpe'a benzer ama sadece hedefin (risk-free) altındaki (downside)
    oynaklığı cezalandırır. downside_deviation=0 ise (hiç kayıp yok) None döner."""
    returns = compute_daily_return_vector(series)
    if len(returns) < 2:
        return None
    daily_rf = risk_free_rate / 252.0
    excess_returns = [r - daily_rf for r in returns]
    mean_excess = sum(excess_returns) / len(excess_returns)
    downside_sq = [min(r - daily_rf, 0.0) ** 2 for r in returns]
    downside_deviation = math.sqrt(sum(downside_sq) / len(downside_sq))
    if downside_deviation == 0:
        return None
    return (mean_excess / downside_deviation) * math.sqrt(252)


def _compute_cagr_pct(series: Dict[date, Decimal]) -> Optional[float]:
    """Yıllıklandırılmış bileşik büyüme oranı (%) — Calmar Ratio için kullanılır."""
    dates = sorted(series.keys())
    if len(dates) < 2:
        return None
    start_val = float(series[dates[0]] or 0)
    end_val = float(series[dates[-1]] or 0)
    if start_val <= 0 or end_val <= 0:
        return None
    days = (dates[-1] - dates[0]).days
    years = days / 365.25
    if years <= 0:
        return None
    cagr = (end_val / start_val) ** (1.0 / years) - 1.0
    return cagr * 100.0


def compute_calmar_ratio(series: Dict[date, Decimal]) -> Optional[float]:
    """Calmar Ratio = Yıllıklandırılmış getiri (CAGR) / |Maksimum Drawdown|."""
    cagr_pct = _compute_cagr_pct(series)
    max_dd_pct = compute_max_drawdown_pct(series)
    if cagr_pct is None or max_dd_pct is None or max_dd_pct == 0:
        return None
    return cagr_pct / abs(max_dd_pct)


def compute_omega_ratio(series: Dict[date, Decimal], target_return: float = 0.0) -> Optional[float]:
    """Omega Ratio = hedefin üstündeki kazançların toplamı / hedefin altındaki kayıpların toplamı.
    target_return günlük getiri bazındadır (varsayılan 0.0)."""
    returns = compute_daily_return_vector(series)
    if len(returns) < 2:
        return None
    gains = sum(r - target_return for r in returns if r > target_return)
    losses = sum(target_return - r for r in returns if r < target_return)
    if losses == 0:
        return None
    return gains / losses


def _historical_percentile(sorted_values: List[float], fraction: float) -> Optional[float]:
    if not sorted_values:
        return None
    index = int(round(fraction * (len(sorted_values) - 1)))
    index = max(0, min(index, len(sorted_values) - 1))
    return sorted_values[index]


def compute_value_at_risk_pct(series: Dict[date, Decimal], confidence: float = 0.95) -> Optional[float]:
    """Tarihsel simülasyon VaR (%). Negatif değer = o güven seviyesinde beklenen en kötü
    günlük getiri eşiği (örn. -3.2 → %95 güvenle günlük kayıp %3.2'yi aşmaz)."""
    returns = compute_daily_return_vector(series)
    if len(returns) < 2:
        return None
    threshold = _historical_percentile(sorted(returns), 1.0 - confidence)
    return threshold * 100.0 if threshold is not None else None


def compute_conditional_var_pct(series: Dict[date, Decimal], confidence: float = 0.95) -> Optional[float]:
    """Conditional VaR / Expected Shortfall (%) — VaR eşiğinin altındaki günlerin ortalama getirisi.
    VaR'dan daha negatif (daha kötü) olmalıdır; kuyruk riskini VaR'dan daha iyi yakalar."""
    returns = compute_daily_return_vector(series)
    if len(returns) < 2:
        return None
    sorted_returns = sorted(returns)
    threshold = _historical_percentile(sorted_returns, 1.0 - confidence)
    if threshold is None:
        return None
    tail = [r for r in sorted_returns if r <= threshold]
    if not tail:
        return None
    return (sum(tail) / len(tail)) * 100.0


def _paired_daily_returns(
    a_series: Dict[date, Decimal],
    b_series: Dict[date, Decimal],
) -> Tuple[List[float], List[float]]:
    """İki seri için ortak tarihlerde hizalanmış (hafta sonu hariç) günlük getiri çiftleri."""
    dates = sorted(set(a_series.keys()) & set(b_series.keys()))
    a_returns: List[float] = []
    b_returns: List[float] = []
    for prev_date, curr_date in zip(dates, dates[1:]):
        if curr_date.weekday() >= 5:
            continue
        a_prev, a_curr = _safe_float_0(a_series[prev_date]), _safe_float_0(a_series[curr_date])
        b_prev, b_curr = _safe_float_0(b_series[prev_date]), _safe_float_0(b_series[curr_date])
        if a_prev > 0 and b_prev > 0:
            a_returns.append((a_curr - a_prev) / a_prev)
            b_returns.append((b_curr - b_prev) / b_prev)
    return a_returns, b_returns


def compute_r_squared(
    portfolio_series: Dict[date, Decimal],
    benchmark_series: Dict[date, Decimal],
) -> Optional[float]:
    """R-Squared — portföy ile benchmark günlük getirileri arasındaki korelasyonun karesi.
    Benchmark hareketinin portföy hareketini ne kadar açıkladığını gösterir (0-1 arası)."""
    port_returns, bench_returns = _paired_daily_returns(portfolio_series, benchmark_series)
    if len(port_returns) < 2:
        return None
    p_mean = sum(port_returns) / len(port_returns)
    b_mean = sum(bench_returns) / len(bench_returns)
    covariance = sum((p - p_mean) * (b - b_mean) for p, b in zip(port_returns, bench_returns))
    p_var = sum((p - p_mean) ** 2 for p in port_returns)
    b_var = sum((b - b_mean) ** 2 for b in bench_returns)
    denom = math.sqrt(p_var * b_var)
    if denom == 0:
        return None
    correlation = covariance / denom
    return correlation ** 2


def compute_tracking_error(
    portfolio_series: Dict[date, Decimal],
    benchmark_series: Dict[date, Decimal],
) -> Optional[float]:
    """Tracking Error (%) — portföy ile benchmark günlük getiri farkının yıllıklandırılmış
    standart sapması. Düşük değer = portföy benchmark'ı yakından takip ediyor."""
    port_returns, bench_returns = _paired_daily_returns(portfolio_series, benchmark_series)
    if len(port_returns) < 2:
        return None
    diffs = [p - b for p, b in zip(port_returns, bench_returns)]
    mean_diff = sum(diffs) / len(diffs)
    variance = sum((d - mean_diff) ** 2 for d in diffs) / (len(diffs) - 1)
    return math.sqrt(variance) * math.sqrt(252) * 100.0


def compute_monthly_returns_matrix(series: Dict[date, Decimal]) -> Dict[int, Dict[int, float]]:
    """Yıl → Ay → o ayın getirisi (%) haritası (aylık getiri ısı haritası ham verisi).
    Her ay için o ay içindeki en son gözlem "ay sonu değeri" kabul edilir."""
    if not series:
        return {}
    month_end_values: Dict[Tuple[int, int], float] = {}
    for d in sorted(series.keys()):
        value = series[d]
        if value is None:
            continue
        month_end_values[(d.year, d.month)] = float(value)

    ordered_keys = sorted(month_end_values.keys())
    result: Dict[int, Dict[int, float]] = {}
    for i in range(1, len(ordered_keys)):
        prev_key, curr_key = ordered_keys[i - 1], ordered_keys[i]
        prev_val, curr_val = month_end_values[prev_key], month_end_values[curr_key]
        if prev_val <= 0:
            continue
        year, month = curr_key
        result.setdefault(year, {})[month] = ((curr_val - prev_val) / prev_val) * 100.0
    return result


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
        return "Yüksek"
    if top_three_weight_pct >= 50:
        return "Orta"
    return "Düşük"


def build_benchmark_insight(benchmark_label: str, gap: Optional[float]) -> str:
    if gap is None:
        return f"{benchmark_label} kıyası için yeterli veri yok."
    if gap >= 0:
        return f"Portföy {benchmark_label} kıyasının %{gap:.2f} üzerinde."
    return f"Portföy {benchmark_label} kıyasının %{abs(gap):.2f} gerisinde."


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
        raw_label = ticker_map.get(stock_id, str(stock_id))
        clean_label = raw_label[:-3] if raw_label.upper().endswith(".IS") else raw_label
        items.append(
            {
                "label": clean_label,
                "current_value": current_value,
                "cost_value": position.total_cost,
                "weight": weight,
                "return_pct": return_pct if return_pct is not None else 0.0,
            }
        )
    return items

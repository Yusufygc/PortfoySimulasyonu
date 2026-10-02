"""
frontier_simulation.py — Verimli Sınır (Efficient Frontier) ve Monte Carlo Simülasyon Motoru.

Sorumluluk:
- Monte Carlo simülasyonu ile 1.000+ rastgele portföy noktası üretme (vektörel ve yüksek performanslı)
- SLSQP ile hedef getiriler üzerinde Verimli Sınır (Efficient Frontier) eğrisi koordinatlarını çıkarma
- Portföy yeniden dengeleme (Rebalance) tutar, adet ve aksiyon hesaplamaları
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


def simulate_monte_carlo(
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
    risk_free_rate: float = 0.30,
    num_simulations: int = 1000,
) -> List[Dict[str, float]]:
    """Vektörel Monte Carlo portföy simülasyonu çalıştırır.

    Dönüş: [{'x': volatilite_yuzde, 'y': getiri_yuzde, 'sharpe': sharpe_orani}, ...]
    """
    n = len(mean_returns)
    if n < 2 or num_simulations <= 0:
        return []

    # Dirichlet dağılımı ile toplamı 1.0 olan rastgele ağırlık matrisi (num_simulations x n)
    weights = np.random.dirichlet(np.ones(n), size=num_simulations)

    port_returns = weights @ mean_returns
    variances = np.einsum("ij,jk,ik->i", weights, cov_matrix, weights)
    port_vols = np.sqrt(np.maximum(variances, 1e-8))

    # Sharpe oranı
    sharpes = np.where(port_vols > 0, (port_returns - risk_free_rate) / port_vols, 0.0)

    points = []
    for i in range(num_simulations):
        points.append(
            {
                "x": round(float(port_vols[i] * 100.0), 2),
                "y": round(float(port_returns[i] * 100.0), 2),
                "sharpe": round(float(sharpes[i]), 3),
            }
        )
    return points


def calculate_efficient_frontier_curve(
    mean_returns: np.ndarray,
    cov_matrix: np.ndarray,
    max_single_weight: float = 0.40,
    points_count: int = 20,
) -> List[Dict[str, float]]:
    """SLSQP ile hedef getiri grid'i üzerinde Verimli Sınır (Efficient Frontier) eğrisi üretir."""
    n = len(mean_returns)
    if n < 2:
        return []

    init_weights = np.array([1.0 / n] * n)
    effective_max_w = max(max_single_weight, 1.0 / n)
    bounds = tuple((0.0, effective_max_w) for _ in range(n))

    # 1. Minimum volatilite portföyünü bul
    try:
        min_res = minimize(
            lambda w: np.sqrt(np.maximum(w @ cov_matrix @ w, 1e-8)),
            init_weights,
            bounds=bounds,
            constraints={"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            method="SLSQP",
        )
        min_ret = float(np.sum(min_res.x * mean_returns))
    except Exception as exc:
        logger.debug("Minimum volatilite bulunamadı: %s", exc)
        min_ret = float(np.min(mean_returns))

    # 2. Kısıtlar altında ulaşılabilecek maksimum getiriyi bul
    try:
        max_res = minimize(
            lambda w: -np.sum(w * mean_returns),
            init_weights,
            bounds=bounds,
            constraints={"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            method="SLSQP",
        )
        max_achievable_ret = float(np.sum(max_res.x * mean_returns)) if max_res.success else float(np.max(mean_returns))
    except Exception as exc:
        logger.debug("Maksimum getiri kısıtı hesaplanamadı: %s", exc)
        max_achievable_ret = float(np.max(mean_returns))

    if max_achievable_ret <= min_ret:
        max_achievable_ret = min_ret + 0.05

    target_returns = np.linspace(min_ret, max_achievable_ret, points_count)
    frontier_pts: List[Dict[str, float]] = []

    for tr in target_returns:
        constraints = (
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "eq", "fun": lambda w, tr=tr: np.sum(w * mean_returns) - tr},
        )
        try:
            res = minimize(
                lambda w: np.sqrt(np.maximum(w @ cov_matrix @ w, 1e-8)),
                init_weights,
                bounds=bounds,
                constraints=constraints,
                method="SLSQP",
            )
            if res.success:
                vol_pct = float(res.fun * 100.0)
                ret_pct = float(tr * 100.0)
                frontier_pts.append({"x": round(vol_pct, 2), "y": round(ret_pct, 2)})
        except Exception:
            continue

    # Volatiliteye göre sıralı döndür
    frontier_pts.sort(key=lambda pt: pt["x"])
    return frontier_pts


def calculate_rebalance_plan(
    total_portfolio_value: float,
    current_weights: Dict[str, float],
    optimal_weights: Dict[str, float],
    last_prices: Optional[Dict[str, float]] = None,
    stock_names: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Mevcut ve optimum ağırlıklara göre parasal ve lot bazlı yeniden dengeleme planı oluşturur."""
    all_symbols = sorted(set(list(current_weights.keys()) + list(optimal_weights.keys())))
    prices = last_prices or {}
    names = stock_names or {}
    tot_val = max(0.0, total_portfolio_value)

    plan = []
    for sym in all_symbols:
        curr_w = float(current_weights.get(sym, 0.0))
        opt_w = float(optimal_weights.get(sym, 0.0))
        diff_w = opt_w - curr_w

        curr_amt = tot_val * (curr_w / 100.0)
        target_amt = tot_val * (opt_w / 100.0)
        diff_amt = target_amt - curr_amt

        if opt_w == 0.0 and curr_w > 0.0:
            action = "AZALT"
        elif curr_w == 0.0 and opt_w > 0.0:
            action = "EKLE"
        elif diff_w > 0.5:
            action = "EKLE"
        elif diff_w < -0.5:
            action = "AZALT"
        else:
            action = "TUT"
            # TUT durumunda rebalance işlemi yapılmaz, pozisyon korunur
            diff_amt = 0.0

        price = float(prices.get(sym, 0.0))
        if action == "TUT" or price <= 0:
            est_shares = 0
            diff_amt = 0.0
        else:
            est_shares = int(round(abs(diff_amt) / price))

        clean_sym = sym.replace(".IS", "").replace(".is", "").strip().upper()
        raw_name = names.get(sym) or names.get(clean_sym) or clean_sym
        comp_name = raw_name.replace(".IS", "").replace(".is", "").strip() if raw_name else clean_sym
        if not comp_name or comp_name.upper() == clean_sym:
            comp_name = clean_sym

        plan.append(
            {
                "symbol": clean_sym,
                "companyName": comp_name,
                "currentWeight": round(curr_w, 2),
                "optimalWeight": round(opt_w, 2),
                "change": round(diff_w, 2),
                "action": action,
                "currentAmount": round(curr_amt, 2),
                "targetAmount": round(target_amt, 2),
                "amountDiff": round(diff_amt, 2),
                "lastPrice": round(price, 2),
                "estShares": est_shares,
            }
        )

    # Optimum ağırlığa göre azalan sırala
    plan.sort(key=lambda item: item["optimalWeight"], reverse=True)
    return plan

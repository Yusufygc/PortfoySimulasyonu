"""Enflasyon / reel büyüme hesaplamaları — saf, ağsız."""
from __future__ import annotations

from typing import Optional


def period_to_month(period: str) -> str:
    """
    isyatirim dönem formatını ay-key'e çevirir.
    "2026/3" → "2026-03", "2025/12" → "2025-12"
    """
    y, m = period.split("/")
    return f"{y}-{int(m):02d}"


def get_yoy_tufe(period: str, tufe_index: dict[str, float]) -> Optional[float]:
    """
    Dönem için YoY TÜFE artışı (%).
    "2026/3" → Mart 2026 endeksi vs Mart 2025 endeksi.
    """
    cur_month  = period_to_month(period)
    y, m       = cur_month.split("-")
    prev_month = f"{int(y) - 1}-{m}"

    cur_idx  = tufe_index.get(cur_month)
    prev_idx = tufe_index.get(prev_month)

    if cur_idx is None or prev_idx is None or prev_idx == 0:
        return None
    return (cur_idx / prev_idx - 1) * 100


def real_growth(nominal_pct: float | None, tufe_pct: float | None) -> Optional[float]:
    """
    Reel büyüme (Fisher etkisi): (1+nom)/(1+tüfe) − 1.
    Her iki argüman % cinsinden (ör. 80.0 = %80).
    """
    if nominal_pct is None or tufe_pct is None:
        return None
    return ((1 + nominal_pct / 100) / (1 + tufe_pct / 100) - 1) * 100

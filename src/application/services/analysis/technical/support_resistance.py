"""
Destek/Direnç seviyeleri — saf fraktal pivot tespiti (bkz. plan §5.1 madde 4).

Yerel tepe (pivot high) / dip (pivot low) barları, ortalanmış (centered)
rolling max/min ile bulunur. Güncel fiyata en yakın destek (altındaki en
yüksek pivot low) ve direnç (üstündeki en düşük pivot high) döndürülür.
"""
from __future__ import annotations

from typing import Optional, Tuple

import pandas as pd


def find_pivot_highs(highs: pd.Series, left: int = 2, right: int = 2) -> pd.Series:
    """Her barın, left/right kadar komşusundan (ortalanmış pencere) yüksek/eşit olduğu maskeyi döner."""
    window = left + right + 1
    centered_max = highs.rolling(window=window, center=True, min_periods=window).max()
    return highs == centered_max


def find_pivot_lows(lows: pd.Series, left: int = 2, right: int = 2) -> pd.Series:
    """Her barın, left/right kadar komşusundan (ortalanmış pencere) düşük/eşit olduğu maskeyi döner."""
    window = left + right + 1
    centered_min = lows.rolling(window=window, center=True, min_periods=window).min()
    return lows == centered_min


def compute_support_resistance(
    highs: pd.Series,
    lows: pd.Series,
    closes: pd.Series,
    left: int = 2,
    right: int = 2,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Serinin son kapanışına en yakın destek/direnç seviyelerini döner.

    Returns:
        (support, resistance) — bulunamazsa None (örn. yeterli pivot yoksa).
    """
    if len(closes) == 0:
        return None, None
    current_price = float(closes.iloc[-1])

    pivot_high_mask = find_pivot_highs(highs, left, right)
    pivot_low_mask = find_pivot_lows(lows, left, right)

    resistance_candidates = highs[pivot_high_mask & (highs > current_price)]
    support_candidates = lows[pivot_low_mask & (lows < current_price)]

    resistance = float(resistance_candidates.min()) if not resistance_candidates.empty else None
    support = float(support_candidates.max()) if not support_candidates.empty else None
    return support, resistance

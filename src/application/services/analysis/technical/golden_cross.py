"""
Golden / Death Cross saf vektörel hesap.

Tek bir kapanış serisinden SMA(short) ile SMA(long) kesişimlerini çıkarır.
Ağsız, durumsuz, IO yok — saf fonksiyon.

Standart:
- SMA(50) > SMA(200) yukarı keser → Golden Cross (boğa sinyali)
- SMA(50) < SMA(200) aşağı keser → Death Cross (ayı sinyali)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Sequence

import pandas as pd

from src.domain.models.golden_cross_event import CrossType


@dataclass(frozen=True)
class DetectedCross:
    """detect_crosses() dönüş değeri — pure veri (DB yok)."""
    cross_date: date
    cross_type: CrossType
    short_ma: Decimal
    long_ma: Decimal
    close_price: Decimal


def detect_crosses(
    closes: pd.Series,
    short: int = 50,
    long: int = 200,
) -> list[DetectedCross]:
    """
    closes: pd.Series — Index=date (sorted asc), value=numeric close.
    Dönüş: kronolojik sırada (en eski önce) tüm cross olayları.

    Yetersiz veri (< long+1 satır) → boş liste.
    """
    if closes is None or len(closes) < long + 1:
        return []

    sma_s = closes.rolling(window=short, min_periods=short).mean()
    sma_l = closes.rolling(window=long,  min_periods=long).mean()
    diff  = sma_s - sma_l
    sign  = diff.gt(0)              # True iff sma_s > sma_l
    prev  = sign.shift(1)

    # Cross noktaları: sign != prev, prev not NaN
    cross_mask = sign.ne(prev) & prev.notna() & sma_l.notna() & sma_s.notna()

    events: list[DetectedCross] = []
    for idx in closes.index[cross_mask]:
        is_golden = bool(sign.loc[idx])
        events.append(DetectedCross(
            cross_date=_as_date(idx),
            cross_type=CrossType.GOLDEN if is_golden else CrossType.DEATH,
            short_ma=Decimal(str(sma_s.loc[idx])),
            long_ma=Decimal(str(sma_l.loc[idx])),
            close_price=Decimal(str(closes.loc[idx])),
        ))
    return events


def _as_date(value) -> date:
    if isinstance(value, date) and not hasattr(value, "hour"):
        return value
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime().date()
    if hasattr(value, "date"):
        return value.date()
    return value

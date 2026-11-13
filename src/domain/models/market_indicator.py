"""Üst piyasa şeridi göstergeleri (kur, altın, gümüş, BIST 100)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class IndicatorQuote:
    """Bir sembolün son fiyatı ve (varsa) önceki kapanışı."""

    last: float
    previous_close: Optional[float] = None


@dataclass(frozen=True)
class MarketIndicator:
    label: str
    value: float
    currency: str  # "₺" veya "" (endeks)
    change_pct: Optional[float] = None  # önceki kapanışa göre %, bilinmiyorsa None

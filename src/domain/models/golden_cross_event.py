"""Golden / Death Cross olay domain modeli."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class CrossType(str, Enum):
    GOLDEN = "GOLDEN"  # SMA(short) yukarı keser SMA(long) — boğa sinyali
    DEATH  = "DEATH"   # SMA(short) aşağı keser SMA(long) — ayı sinyali


@dataclass(frozen=True)
class GoldenCrossEvent:
    """EMA50 ile EMA200 kesişimi (cross_events tablosunun domain karşılığı). Ticker anahtarlıdır (uzantısız)."""
    id: Optional[int]
    ticker: str
    cross_date: date
    cross_type: CrossType
    short_ma: Optional[Decimal]
    long_ma: Optional[Decimal]
    close_price: Decimal
    detected_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.ticker:
            raise ValueError("ticker is required")
        if not isinstance(self.cross_type, CrossType):
            object.__setattr__(self, "cross_type", CrossType(self.cross_type))
        if self.close_price <= 0:
            raise ValueError("close_price must be positive")

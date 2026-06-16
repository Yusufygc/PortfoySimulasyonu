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
    """SMA50 ile SMA200 kesişimi (golden_cross_events tablosunun domain karşılığı)."""
    id: Optional[int]
    stock_id: int
    ticker: str
    cross_date: date
    cross_type: CrossType
    short_ma: Optional[Decimal]
    long_ma: Optional[Decimal]
    close_price: Decimal
    detected_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.stock_id <= 0:
            raise ValueError("stock_id must be positive")
        if not isinstance(self.cross_type, CrossType):
            object.__setattr__(self, "cross_type", CrossType(self.cross_type))
        if self.close_price <= 0:
            raise ValueError("close_price must be positive")

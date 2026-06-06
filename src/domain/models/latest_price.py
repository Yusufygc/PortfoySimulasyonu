from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class LatestPrice:
    """
    Latest/intraday price cache for UI valuation.

    This is intentionally separate from DailyPrice: it is not an end-of-day
    historical close and must not be used by reports or backtests.
    """

    id: Optional[int]
    stock_id: int
    price: Decimal
    as_of: datetime
    source: str
    provider: str
    fetched_at: datetime

    def __post_init__(self) -> None:
        if self.stock_id <= 0:
            raise ValueError("Stock id must be positive")

        price = self.price if isinstance(self.price, Decimal) else Decimal(str(self.price))
        if price <= 0:
            raise ValueError("Latest price must be positive")
        object.__setattr__(self, "price", price)

        source = (self.source or "").strip()
        if not source:
            raise ValueError("Latest price source is required")
        object.__setattr__(self, "source", source)

        provider = (self.provider or "").strip()
        if not provider:
            raise ValueError("Latest price provider is required")
        object.__setattr__(self, "provider", provider)

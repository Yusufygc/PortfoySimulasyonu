# src/domain/models/daily_price.py

from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class DailyPrice:
    """
    Tek bir hisse için bir güne ait kapanış fiyatı.
    DB'deki daily_prices tablosunun domain karşılığı.
    """
    id: Optional[int]
    stock_id: int
    price_date: date
    close_price: Decimal
    currency_code: str = "TRY"
    source: str = "yfinance"

    def __post_init__(self) -> None:
        if self.stock_id <= 0:
            raise ValueError("Stock id must be positive")

        close_price = self.close_price if isinstance(self.close_price, Decimal) else Decimal(str(self.close_price))
        if close_price <= 0:
            raise ValueError("Close price must be positive")
        object.__setattr__(self, "close_price", close_price)

        currency_code = (self.currency_code or "").strip().upper()
        if not currency_code:
            raise ValueError("Currency code is required")
        object.__setattr__(self, "currency_code", currency_code)

        source = (self.source or "").strip()
        if not source:
            raise ValueError("Price source is required")
        object.__setattr__(self, "source", source)

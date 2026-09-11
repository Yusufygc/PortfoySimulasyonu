# src/domain/models/daily_price.py

from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class DailyPrice:
    """
    Tek bir hisse için bir güne ait fiyat/hacim verisi.
    DB'deki daily_prices tablosunun domain karşılığı.

    open_price/high_price/low_price/volume opsiyoneldir (Optional) —
    eski kayıtlarda ve close-only veri kaynaklarında None olabilir.
    ATR/Stochastic/CCI/VWAP/OBV gibi OHLCV-bağımlı indikatörler bu alanlar
    doluyken hesaplanabilir (bkz. TRANSFORMATION_PLAN.md Faz 2).
    """
    id: Optional[int]
    stock_id: int
    price_date: date
    close_price: Decimal
    currency_code: str = "TRY"
    source: str = "yfinance"
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    volume: Optional[int] = None

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

        object.__setattr__(self, "open_price", self._optional_positive_decimal(self.open_price))
        object.__setattr__(self, "high_price", self._optional_positive_decimal(self.high_price))
        object.__setattr__(self, "low_price", self._optional_positive_decimal(self.low_price))

        if self.volume is not None and self.volume < 0:
            raise ValueError("Volume must not be negative")

    @staticmethod
    def _optional_positive_decimal(value: Optional[Decimal]) -> Optional[Decimal]:
        if value is None:
            return None
        decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
        if decimal_value <= 0:
            raise ValueError("OHLC price fields must be positive when provided")
        return decimal_value

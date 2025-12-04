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

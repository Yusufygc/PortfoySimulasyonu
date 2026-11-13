"""Piyasa geçmişi (OLAP) günlük bar modeli — hisse kimliğinden bağımsız, ticker bazlı."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class MarketBar:
    """DuckDB piyasa geçmişindeki tek bir günlük OHLCV barı (ticker `.IS` uzantısız tutulur)."""

    ticker: str
    price_date: date
    close_price: float
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    volume: Optional[int] = None

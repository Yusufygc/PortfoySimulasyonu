# src/domain/models/stock.py

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Stock:
    """
    'stocks' tablosunun domain karşılığı.

    Not:
      - DB tablosunda created_at / updated_at var ama domain tarafında
        çoğu iş kuralı için çok kritik değil. Yine de ekliyoruz.
    """
    id: Optional[int]
    ticker: str                 # Örn: "AKBNK.IS"
    name: Optional[str] = None  # Örn: "Akbank T.A.Ş."
    currency_code: str = "TRY"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        ticker = (self.ticker or "").strip().upper()
        if not ticker:
            raise ValueError("Ticker is required")
        object.__setattr__(self, "ticker", ticker)

        currency_code = (self.currency_code or "").strip().upper()
        if not currency_code:
            raise ValueError("Currency code is required")
        object.__setattr__(self, "currency_code", currency_code)

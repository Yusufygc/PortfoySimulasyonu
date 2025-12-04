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

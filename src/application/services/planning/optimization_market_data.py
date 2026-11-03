from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol

import pandas as pd

from src.domain.constants.finance import DEFAULT_ANNUAL_RISK_FREE_RATE


@dataclass(frozen=True)
class OptimizationPolicy:
    trading_days_per_year: int = 252
    risk_free_rate: float = DEFAULT_ANNUAL_RISK_FREE_RATE
    max_single_weight: float = 0.40


class OptimizationMarketDataProvider(Protocol):
    def get_historical_prices(self, tickers: List[str], days: int, min_columns: int = 2) -> pd.DataFrame:
        """`min_columns`: sonuçta en az bu kadar geçerli sütun yoksa kaynak yetersiz sayılır (portföy optimizasyonu 2, birleşik portföyün BIST kısmı 1)."""
        ...

    def get_last_price(self, ticker: str) -> Optional[float]:
        ...

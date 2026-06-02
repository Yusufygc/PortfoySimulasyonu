from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol

import pandas as pd


@dataclass(frozen=True)
class OptimizationPolicy:
    trading_days_per_year: int = 252
    risk_free_rate: float = 0.30
    max_single_weight: float = 0.40


class OptimizationMarketDataProvider(Protocol):
    def get_historical_prices(self, tickers: List[str], days: int) -> pd.DataFrame:
        ...

    def get_last_price(self, ticker: str) -> Optional[float]:
        ...

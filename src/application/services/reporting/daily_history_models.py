# src/application/services/daily_history_models.py

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

class ExportMode(str, Enum):
    OVERWRITE = "overwrite"
    APPEND = "append"

@dataclass
class DailyPosition:
    date: date
    ticker: str
    quantity: int
    avg_cost: Decimal
    cost_basis: Decimal
    close_price: Optional[Decimal]
    position_value: Optional[Decimal]
    daily_price_change_pct: Optional[Decimal]
    daily_pnl_tl: Optional[Decimal]
    unrealized_pnl_tl: Optional[Decimal]
    unrealized_pnl_pct: Optional[Decimal]
    weight_pct: Optional[Decimal]

@dataclass
class DailyPortfolioSnapshot:
    total_cost_basis: Optional[Decimal]
    date: date
    total_value: Optional[Decimal]
    daily_return_pct: Optional[Decimal]
    cumulative_return_pct: Optional[Decimal]
    daily_pnl: Optional[Decimal]
    cumulative_pnl: Optional[Decimal]
    status: str

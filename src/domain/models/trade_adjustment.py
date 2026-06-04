# src/domain/models/trade_adjustment.py

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

@dataclass(frozen=True)
class TradeAdjustment:
    id: Optional[int]
    trade_id: int
    corporate_action_id: int
    factor: Decimal
    pre_quantity: int
    post_quantity: int
    pre_price: Decimal
    post_price: Decimal
    applied_at: datetime

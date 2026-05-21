from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from src.domain.models.portfolio import Portfolio


@dataclass
class SimulationState:
    portfolio: Portfolio = field(default_factory=Portfolio)
    trade_cursor: int = 0
    last_close_by_stock: dict[int, Decimal] = field(default_factory=dict)
    last_portfolio_value: Decimal | None = None
    base_portfolio_value: Decimal | None = None

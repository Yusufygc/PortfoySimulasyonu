"""Uygulanmış (veya geri alınmış) bölünme olayı ve denetim izi (saf domain modelleri).

Bir olay üç deftere birden dokunabilir: ana portföy (`trades`), model portföyler (`model_portfolio_trades`) ve
Portföyüm varlık defteri (`asset_trades`). Her işlem değişikliği ve küsurat nakdi kaydı olayla birlikte saklanır;
geri alma bu kayıtlardan yapılır.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple

from src.domain.split_math import LedgerLot


class SplitLedger(str, Enum):
    MAIN = "MAIN"
    MODEL = "MODEL"
    ASSET = "ASSET"


class SplitEventStatus(str, Enum):
    APPLIED = "APPLIED"
    REVERTED = "REVERTED"


@dataclass(frozen=True)
class SplitTradeChange:
    ledger: SplitLedger
    trade_id: int
    pre_quantity: Decimal
    post_quantity: Decimal
    pre_price: Decimal
    post_price: Decimal
    portfolio_id: Optional[int] = None  # model portföy işlemlerinde


@dataclass(frozen=True)
class SplitCashEntry:
    """Küsurat nakdi: ana portföyde `cash_movements`, model portföyde `model_portfolio_cash_movements` kaydı."""
    ledger: SplitLedger
    amount: Decimal
    movement_date: date
    portfolio_id: Optional[int] = None
    movement_id: Optional[int] = None


@dataclass(frozen=True)
class SplitEvent:
    id: Optional[int]
    ticker: str
    ex_date: date
    multiplier: Decimal
    sources: str                       # "PRICE_BREAK,YAHOO" gibi
    auto_applied: bool
    status: SplitEventStatus = SplitEventStatus.APPLIED
    stock_id: Optional[int] = None
    asset_id: Optional[int] = None
    corporate_action_id: Optional[int] = None
    applied_at: Optional[datetime] = None
    reverted_at: Optional[datetime] = None
    note: Optional[str] = None
    price_adjusted_before: Optional[date] = None
    price_adjustment_count: int = 0
    market_effective_date: Optional[date] = None
    trade_changes: Tuple[SplitTradeChange, ...] = field(default_factory=tuple)
    cash_entries: Tuple[SplitCashEntry, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if (self.stock_id is None) == (self.asset_id is None):
            raise ValueError("Split event needs exactly one of stock_id or asset_id")
        if not isinstance(self.status, SplitEventStatus):
            object.__setattr__(self, "status", SplitEventStatus(self.status))


LedgerKey = Tuple[SplitLedger, Optional[int]]  # (defter, model portföy id)


@dataclass(frozen=True)
class SplitLedgerSnapshot:
    """Bir hisse/varlığın tüm defterlerdeki işlemleri: anahtar (defter, model portföy id) -> lotlar."""
    lots: Dict[LedgerKey, List[LedgerLot]] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return not any(self.lots.values())

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from .position import Position
from .trade import TradeSide

ZERO = Decimal("0")

INSUFFICIENT_CASH = "insufficient_cash"
INSUFFICIENT_LOTS = "insufficient_lots"


@dataclass(frozen=True)
class TradeImpact:
    """Emir uygulanırsa pozisyonun ve nakdin alacağı hal (ön izleme; hiçbir şey kaydedilmez)."""

    valid: bool
    reason: str                         # "", INSUFFICIENT_CASH veya INSUFFICIENT_LOTS
    new_quantity: int
    new_avg_cost: Optional[Decimal]
    cash_after: Optional[Decimal]       # nakit bilinmiyorsa None


def preview_order(
    side: TradeSide,
    quantity: int,
    price: Decimal,
    current_quantity: int,
    current_avg_cost: Decimal,
    cash: Optional[Decimal],
) -> TradeImpact:
    """Alım/satım ön izlemesi; yetersiz nakit ve yetersiz lot burada karara bağlanır (arayüz yalnızca biçimler)."""
    quantity = max(0, int(quantity))
    price = price if price and price > 0 else ZERO
    total = price * Decimal(quantity)
    position = Position(stock_id=0, total_quantity=current_quantity, total_cost=current_avg_cost * Decimal(current_quantity))
    new_quantity, new_avg = position.preview_trade(side, quantity, price)  # domain kuralı
    cash_after = None if cash is None else (cash - total if side == TradeSide.BUY else cash + total)

    reason = ""
    if side == TradeSide.BUY and cash_after is not None and cash_after < 0:
        reason = INSUFFICIENT_CASH
    elif side == TradeSide.SELL and new_quantity < 0:
        reason = INSUFFICIENT_LOTS
    return TradeImpact(
        valid=quantity > 0 and price > 0 and not reason,
        reason=reason,
        new_quantity=new_quantity,
        new_avg_cost=new_avg,
        cash_after=cash_after,
    )

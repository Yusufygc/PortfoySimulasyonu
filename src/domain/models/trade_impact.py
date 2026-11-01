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


@dataclass(frozen=True)
class OrderSpec:
    """Önizlenecek emir: yön, lot, birim fiyat ve ücret (TL)."""

    side: TradeSide
    quantity: int
    price: Decimal
    fee: Decimal = ZERO


def _rejection_reason(side: TradeSide, new_quantity: int, cash_after: Optional[Decimal]) -> str:
    if side == TradeSide.BUY:
        return INSUFFICIENT_CASH if cash_after is not None and cash_after < 0 else ""
    return INSUFFICIENT_LOTS if new_quantity < 0 else ""


def preview_order(order: OrderSpec, current_quantity: int, current_avg_cost: Decimal, cash: Optional[Decimal]) -> TradeImpact:
    """Alım/satım ön izlemesi; yetersiz nakit ve yetersiz lot burada karara bağlanır (arayüz yalnızca biçimler)."""
    side, fee = order.side, order.fee
    quantity = max(0, int(order.quantity))
    price = order.price if order.price and order.price > 0 else ZERO
    total = price * Decimal(quantity)
    position = Position(stock_id=0, total_quantity=current_quantity, total_cost=current_avg_cost * Decimal(current_quantity))
    new_quantity, new_avg = position.preview_trade(side, quantity, price, fee)  # domain kuralı (ücret alımda maliyete girer)
    cash_after = None if cash is None else (cash - total - fee if side == TradeSide.BUY else cash + total - fee)

    reason = _rejection_reason(side, new_quantity, cash_after)
    return TradeImpact(
        valid=quantity > 0 and price > 0 and not reason,
        reason=reason,
        new_quantity=new_quantity,
        new_avg_cost=new_avg,
        cash_after=cash_after,
    )

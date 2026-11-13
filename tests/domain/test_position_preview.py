"""Position.preview_trade: emir ön izlemesi domain kuralıyla (Decimal) hesaplanır."""
from __future__ import annotations

from decimal import Decimal

from src.domain.models.position import Position
from src.domain.models.trade import TradeSide

D = Decimal


def _position(qty: int, avg: str) -> Position:
    return Position(stock_id=1, total_quantity=qty, total_cost=D(avg) * qty)


def test_buy_preview_weighted_average_cost():
    assert _position(100, "10").preview_trade(TradeSide.BUY, 100, D("20")) == (200, D("15"))


def test_sell_keeps_average_and_closing_returns_none():
    assert _position(100, "10").preview_trade(TradeSide.SELL, 40, D("50")) == (60, D("10"))
    assert _position(100, "10").preview_trade(TradeSide.SELL, 100, D("50")) == (0, None)


def test_oversell_returns_negative_quantity_and_position_unchanged():
    position = _position(10, "10")
    assert position.preview_trade(TradeSide.SELL, 15, D("5"))[0] == -5
    assert position.total_quantity == 10 and position.total_cost == D("100")


def test_preview_is_exact_decimal_not_float():
    new_qty, new_avg = _position(3, "0.1").preview_trade(TradeSide.BUY, 3, D("0.2"))
    assert new_qty == 6 and new_avg == D("0.15")

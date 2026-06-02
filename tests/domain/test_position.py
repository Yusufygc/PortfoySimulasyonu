from datetime import date, time
from decimal import Decimal

import pytest

from src.domain.models.position import Position
from src.domain.models.trade import Trade


def test_from_trades_sorts_none_trade_time_before_timed_trade_on_same_day():
    timed_buy = Trade.create_buy(
        stock_id=1,
        trade_date=date(2026, 1, 1),
        quantity=5,
        price=Decimal("20.0"),
        trade_time=time(10, 30),
    )
    untimed_buy = Trade.create_buy(
        stock_id=1,
        trade_date=date(2026, 1, 1),
        quantity=10,
        price=Decimal("10.0"),
        trade_time=None,
    )

    position = Position.from_trades(stock_id=1, trades=[timed_buy, untimed_buy])

    assert position.trades == [untimed_buy, timed_buy]
    assert position.total_quantity == 15
    assert position.average_cost == Decimal("13.33333333333333333333333333")


def test_apply_trade_does_not_mutate_position_when_sell_exceeds_quantity():
    position = Position(stock_id=1)
    buy_trade = Trade.create_buy(
        stock_id=1,
        trade_date=date(2026, 1, 1),
        quantity=10,
        price=Decimal("10.0"),
    )
    invalid_sell = Trade.create_sell(
        stock_id=1,
        trade_date=date(2026, 1, 2),
        quantity=20,
        price=Decimal("15.0"),
    )

    position.apply_trade(buy_trade)

    with pytest.raises(ValueError, match="Cannot sell more"):
        position.apply_trade(invalid_sell)

    assert position.trades == [buy_trade]
    assert position.total_quantity == 10
    assert position.total_cost == Decimal("100.0")
    assert position.realized_pl == Decimal("0")

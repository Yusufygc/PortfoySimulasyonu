import pytest
from datetime import date
from decimal import Decimal
from src.domain.models.trade import Trade, TradeSide

def test_create_buy_trade_success():
    trade = Trade.create_buy(
        stock_id=1,
        trade_date=date(2026, 1, 1),
        quantity=10,
        price=Decimal("15.5")
    )
    assert trade.side == TradeSide.BUY
    assert trade.quantity == 10
    assert trade.price == Decimal("15.5")
    assert trade.total_amount == Decimal("155.0")

def test_create_sell_trade_success():
    trade = Trade.create_sell(
        stock_id=1,
        trade_date=date(2026, 1, 2),
        quantity=5,
        price=Decimal("20.0")
    )
    assert trade.side == TradeSide.SELL
    assert trade.quantity == 5
    assert trade.price == Decimal("20.0")
    assert trade.total_amount == Decimal("100.0")

def test_create_trade_invalid_quantity():
    with pytest.raises(ValueError):
        Trade.create_buy(
            stock_id=1,
            trade_date=date(2026, 1, 1),
            quantity=-5,
            price=Decimal("15.0")
        )

def test_create_trade_invalid_price():
    with pytest.raises(ValueError):
        Trade.create_sell(
            stock_id=1,
            trade_date=date(2026, 1, 1),
            quantity=5,
            price=Decimal("-10.0")
        )

import pytest
from datetime import date
from decimal import Decimal
from src.domain.models.portfolio import Portfolio
from src.domain.models.trade import Trade

@pytest.fixture
def empty_portfolio():
    return Portfolio()

def test_apply_buy_trade(empty_portfolio):
    trade = Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=100, price=Decimal("10.0"))
    empty_portfolio.apply_trade(trade)
    
    pos = empty_portfolio.get_position(1)
    assert pos.total_quantity == 100
    assert pos.average_cost == Decimal("10.0")
    assert empty_portfolio.total_cost() == Decimal("1000.0")

def test_apply_sell_trade(empty_portfolio):
    buy_trade = Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=100, price=Decimal("10.0"))
    empty_portfolio.apply_trade(buy_trade)
    
    sell_trade = Trade.create_sell(stock_id=1, trade_date=date(2026, 1, 2), quantity=50, price=Decimal("15.0"))
    empty_portfolio.apply_trade(sell_trade)
    
    pos = empty_portfolio.get_position(1)
    assert pos.total_quantity == 50
    assert pos.realized_pl == Decimal("250.0")  # 50 * (15 - 10)

def test_sell_more_than_owned(empty_portfolio):
    buy_trade = Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=10, price=Decimal("10.0"))
    empty_portfolio.apply_trade(buy_trade)
    
    sell_trade = Trade.create_sell(stock_id=1, trade_date=date(2026, 1, 2), quantity=20, price=Decimal("15.0"))
    
    with pytest.raises(ValueError):
        empty_portfolio.apply_trade(sell_trade)

from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.application.services.portfolio.trade_entry_service import TradeEntryService
from src.application.services.portfolio.portfolio_service import PortfolioService
from src.domain.models.cash_movement import CashMovement
from src.domain.models.stock import Stock
from src.domain.models.trade import Trade, TradeSide


class FakeStockRepo:
    def __init__(self):
        self.by_id = {}
        self.by_ticker = {}
        self.next_id = 1

    def get_stock_by_id(self, stock_id):
        return self.by_id.get(stock_id)

    def get_stock_by_ticker(self, ticker):
        return self.by_ticker.get(ticker)

    def insert_stock(self, stock):
        saved = Stock(
            id=self.next_id,
            ticker=stock.ticker,
            name=stock.name,
            currency_code=stock.currency_code,
        )
        self.by_id[self.next_id] = saved
        self.by_ticker[saved.ticker] = saved
        self.next_id += 1
        return saved


class FakePortfolioService:
    def __init__(self):
        self.saved_trades = []

    def add_trade(self, trade):
        self.saved_trades.append(trade)
        return trade

    def get_cash_balance(self, as_of=None):
        return Decimal("1000000")

    def validate_trade(self, trade):
        pass


class FakePortfolioRepo:
    def __init__(self, trades=None):
        self.trades = trades or []
        self.insert_calls = []

    def get_all_trades(self):
        return list(self.trades)

    def insert_trade(self, trade):
        self.insert_calls.append(trade)
        self.trades.append(trade)
        return trade


class FakePriceRepo:
    pass


class FakeCashMovementRepo:
    def __init__(self, movements=None):
        self.movements = movements or []

    def get_all_movements(self):
        return list(self.movements)

    def get_movements_until(self, movement_date, movement_time=None):
        return [movement for movement in self.movements if movement.movement_date <= movement_date]


class FakeClosedMarketSessionService:
    def status_for(self, trade_date, trade_time=None):
        return SimpleNamespace(is_open=False, message="Kapali")


def test_submit_trade_creates_missing_stock_and_buy_trade():
    stock_repo = FakeStockRepo()
    portfolio_service = FakePortfolioService()
    service = TradeEntryService(stock_repo=stock_repo, portfolio_service=portfolio_service)

    result = service.submit_trade(
        ticker="asels",
        side=TradeSide.BUY,
        quantity=10,
        price=Decimal("12.5"),
        trade_date=date(2026, 1, 2),
        trade_time=time(10, 30),
        name="ASELSAN",
    )

    assert result.stock_id == 1
    assert result.ticker == "ASELS.IS"
    assert stock_repo.get_stock_by_ticker("ASELS.IS").name == "ASELSAN"
    assert portfolio_service.saved_trades[0].stock_id == 1
    assert portfolio_service.saved_trades[0].side == TradeSide.BUY


def test_submit_trade_rejects_closed_market_session_before_saving():
    stock_repo = FakeStockRepo()
    portfolio_service = FakePortfolioService()
    service = TradeEntryService(
        stock_repo=stock_repo,
        portfolio_service=portfolio_service,
        market_session_service=FakeClosedMarketSessionService(),
    )

    with pytest.raises(ValueError, match="BIST"):
        service.submit_trade(
            ticker="asels",
            side=TradeSide.BUY,
            quantity=10,
            price=Decimal("12.5"),
            trade_date=date(2026, 6, 6),
            trade_time=time(11, 0),
        )

    assert portfolio_service.saved_trades == []


def test_submit_trade_reuses_existing_stock_by_id():
    stock_repo = FakeStockRepo()
    existing = stock_repo.insert_stock(Stock(id=None, ticker="THYAO.IS", name="THYAO", currency_code="TRY"))
    portfolio_service = FakePortfolioService()
    service = TradeEntryService(stock_repo=stock_repo, portfolio_service=portfolio_service)

    result = service.submit_trade(
        ticker="thyao",
        stock_id=existing.id,
        side=TradeSide.SELL,
        quantity=3,
        price=Decimal("100"),
        trade_date=date(2026, 1, 5),
    )

    assert result.stock_id == existing.id
    assert portfolio_service.saved_trades[0].side == TradeSide.SELL
    assert portfolio_service.saved_trades[0].stock_id == existing.id


def test_submit_trade_rejects_buy_when_cash_is_insufficient():
    stock_repo = FakeStockRepo()
    portfolio_repo = FakePortfolioRepo()
    portfolio_service = PortfolioService(
        portfolio_repo,
        FakePriceRepo(),
        cash_movement_repo=FakeCashMovementRepo(),
    )
    service = TradeEntryService(stock_repo=stock_repo, portfolio_service=portfolio_service)

    try:
        service.submit_trade(
            ticker="asels",
            side=TradeSide.BUY,
            quantity=10,
            price=Decimal("12.5"),
            trade_date=date(2026, 1, 2),
        )
    except ValueError as exc:
        assert "yeterli sermayeniz yoktu" in str(exc)
    else:
        raise AssertionError("Expected insufficient cash error")

    assert portfolio_repo.insert_calls == []


def test_submit_trade_accepts_buy_after_deposit_and_sell_adds_cash():
    stock_repo = FakeStockRepo()
    stock = stock_repo.insert_stock(Stock(id=None, ticker="ASELS.IS", name="ASELS", currency_code="TRY"))
    portfolio_repo = FakePortfolioRepo()
    cash_repo = FakeCashMovementRepo(
        [CashMovement.create_deposit(Decimal("200"), date(2026, 1, 1))]
    )
    portfolio_service = PortfolioService(portfolio_repo, FakePriceRepo(), cash_movement_repo=cash_repo)
    service = TradeEntryService(stock_repo=stock_repo, portfolio_service=portfolio_service)

    service.submit_trade(
        ticker="ASELS",
        stock_id=stock.id,
        side=TradeSide.BUY,
        quantity=10,
        price=Decimal("10"),
        trade_date=date(2026, 1, 2),
    )
    service.submit_trade(
        ticker="ASELS",
        stock_id=stock.id,
        side=TradeSide.SELL,
        quantity=4,
        price=Decimal("12"),
        trade_date=date(2026, 1, 3),
    )

    assert portfolio_service.get_cash_balance() == Decimal("148")


def test_submit_trade_rejects_sell_above_available_lot():
    stock_repo = FakeStockRepo()
    stock = stock_repo.insert_stock(Stock(id=None, ticker="ASELS.IS", name="ASELS", currency_code="TRY"))
    portfolio_repo = FakePortfolioRepo(
        [Trade.create_buy(stock_id=stock.id, trade_date=date(2026, 1, 2), quantity=3, price=Decimal("10"))]
    )
    portfolio_service = PortfolioService(portfolio_repo, FakePriceRepo())
    service = TradeEntryService(stock_repo=stock_repo, portfolio_service=portfolio_service)

    try:
        service.submit_trade(
            ticker="ASELS",
            stock_id=stock.id,
            side=TradeSide.SELL,
            quantity=4,
            price=Decimal("12"),
            trade_date=date(2026, 1, 3),
        )
    except ValueError as exc:
        assert "yeterli pozisyonunuz yoktu" in str(exc)
    else:
        raise AssertionError("Expected insufficient position error")

    assert portfolio_repo.insert_calls == []

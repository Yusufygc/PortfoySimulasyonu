from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.application.services.portfolio.trade_entry_service import TradeEntryService
from src.application.services.planning.model_portfolio_service import ModelPortfolioService
from src.domain.models.model_portfolio import ModelPortfolio, ModelPortfolioCashMovement, ModelPortfolioTrade
from src.domain.models.stock import Stock
from src.domain.models.trade import TradeSide


class FakeModelPortfolioRepo:
    def __init__(self):
        self.portfolios = {
            1: ModelPortfolio(id=1, name="Deneme", initial_cash=Decimal("1000")),
        }
        self.trades = {
            1: [
                ModelPortfolioTrade.create_buy(
                    portfolio_id=1,
                    stock_id=10,
                    trade_date=date(2026, 1, 1),
                    quantity=10,
                    price=Decimal("10"),
                ),
                ModelPortfolioTrade.create_sell(
                    portfolio_id=1,
                    stock_id=10,
                    trade_date=date(2026, 1, 2),
                    quantity=2,
                    price=Decimal("15"),
                ),
            ]
        }
        self.cash_movements = {1: []}

    def get_all_model_portfolios(self):
        return list(self.portfolios.values())

    def get_model_portfolio_by_id(self, portfolio_id):
        return self.portfolios.get(portfolio_id)

    def get_trades_by_portfolio_id(self, portfolio_id):
        return list(self.trades.get(portfolio_id, []))

    def count_trades_by_portfolio_id(self, portfolio_id):
        return len(self.trades.get(portfolio_id, []))

    def create_model_portfolio(self, portfolio):
        return portfolio

    def update_model_portfolio(self, portfolio):
        self.portfolios[portfolio.id] = portfolio

    def delete_model_portfolio(self, portfolio_id):
        self.portfolios.pop(portfolio_id, None)
        self.trades.pop(portfolio_id, None)

    def insert_trade(self, trade):
        self.trades.setdefault(trade.portfolio_id, []).append(trade)
        return trade

    def delete_trade(self, trade_id):
        return None

    def get_cash_movements_by_portfolio_id(self, portfolio_id):
        return list(self.cash_movements.get(portfolio_id, []))

    def insert_cash_movement(self, movement):
        saved = ModelPortfolioCashMovement(
            id=len(self.cash_movements.get(movement.portfolio_id, [])) + 1,
            portfolio_id=movement.portfolio_id,
            movement_date=movement.movement_date,
            movement_time=movement.movement_time,
            type=movement.type,
            amount=movement.amount,
            notes=movement.notes,
        )
        self.cash_movements.setdefault(movement.portfolio_id, []).append(saved)
        return saved


class FakeStockRepo:
    def __init__(self):
        self.stocks = {
            10: Stock(id=10, ticker="ASELS.IS", name="ASELSAN", currency_code="TRY"),
        }

    def get_stock_by_id(self, stock_id):
        return self.stocks.get(stock_id)

    def get_stocks_by_ids(self, stock_ids):
        return [self.stocks[stock_id] for stock_id in stock_ids if stock_id in self.stocks]

    def get_stock_by_ticker(self, ticker):
        return next((stock for stock in self.stocks.values() if stock.ticker == ticker), None)

    def insert_stock(self, stock):
        saved = Stock(id=max(self.stocks) + 1, ticker=stock.ticker, name=stock.name, currency_code=stock.currency_code)
        self.stocks[saved.id] = saved
        return saved


class FakeClosedMarketSessionService:
    def status_for(self, trade_date, trade_time=None):
        return SimpleNamespace(is_open=False, message="Kapali")


def test_model_portfolio_service_computes_remaining_cash_and_summary():
    service = ModelPortfolioService(FakeModelPortfolioRepo(), FakeStockRepo())

    remaining_cash = service.get_remaining_cash(1)
    summary = service.get_portfolio_summary(1, price_map={10: Decimal("12")})

    assert remaining_cash == Decimal("930")
    assert summary["positions_value"] == Decimal("96")
    assert summary["total_value"] == Decimal("1026")
    assert summary["profit_loss"] == Decimal("26")
    assert summary["net_capital"] == Decimal("1000")


def test_model_portfolio_service_returns_positions_with_details():
    service = ModelPortfolioService(FakeModelPortfolioRepo(), FakeStockRepo())

    positions = service.get_positions_with_details(1, price_map={10: Decimal("12")})

    assert len(positions) == 1
    assert positions[0]["ticker"] == "ASELS.IS"
    assert positions[0]["quantity"] == 8
    assert positions[0]["current_value"] == Decimal("96")
    assert positions[0]["profit_loss"] == Decimal("16")


def test_model_portfolio_rejects_closed_market_session_before_saving_trade():
    repo = FakeModelPortfolioRepo()
    service = ModelPortfolioService(
        repo,
        FakeStockRepo(),
        market_session_service=FakeClosedMarketSessionService(),
    )

    with pytest.raises(ValueError, match="BIST"):
        service.add_trade_by_ticker(
            portfolio_id=1,
            ticker="ASELS",
            side="BUY",
            quantity=1,
            price=Decimal("10"),
            trade_date=date(2026, 6, 6),
            trade_time=time(11, 0),
        )

    assert len(repo.trades[1]) == 2


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


def test_dashboard_and_model_portfolio_reuse_same_stock_for_same_ticker():
    stock_repo = FakeStockRepo()
    dashboard_service = TradeEntryService(
        stock_repo=stock_repo,
        portfolio_service=FakePortfolioService(),
    )
    model_service = ModelPortfolioService(FakeModelPortfolioRepo(), stock_repo)

    dashboard_result = dashboard_service.submit_trade(
        ticker="asels",
        side=TradeSide.BUY,
        quantity=1,
        price=Decimal("10"),
        trade_date=date(2026, 1, 3),
        name="ASELSAN",
    )
    model_trade = model_service.add_trade_by_ticker(
        portfolio_id=1,
        ticker="ASELS",
        side="BUY",
        quantity=1,
        price=Decimal("10"),
        trade_date=date(2026, 1, 3),
    )

    assert dashboard_result.stock_id == 10
    assert model_trade.stock_id == dashboard_result.stock_id


def test_model_portfolio_rejects_buy_when_cash_is_insufficient():
    service = ModelPortfolioService(FakeModelPortfolioRepo(), FakeStockRepo())

    try:
        service.add_trade_by_ticker(
            portfolio_id=1,
            ticker="ASELS",
            side="BUY",
            quantity=1000,
            price=Decimal("10"),
            trade_date=date(2026, 1, 3),
        )
    except ValueError as exc:
        assert "Yetersiz nakit" in str(exc)
    else:
        raise AssertionError("Expected insufficient model cash error")


def test_model_portfolio_rejects_sell_for_missing_stock_without_creating_stock():
    stock_repo = FakeStockRepo()
    service = ModelPortfolioService(FakeModelPortfolioRepo(), stock_repo)
    before_ids = set(stock_repo.stocks)

    try:
        service.add_trade_by_ticker(
            portfolio_id=1,
            ticker="XXXX",
            side="SELL",
            quantity=1,
            price=Decimal("10"),
            trade_date=date(2026, 1, 3),
        )
    except ValueError as exc:
        assert "Hisse bulunamadi" in str(exc)
    else:
        raise AssertionError("Expected missing stock error")

    assert set(stock_repo.stocks) == before_ids


def test_model_portfolio_capital_deposit_increases_cash_without_profit():
    service = ModelPortfolioService(FakeModelPortfolioRepo(), FakeStockRepo())

    movement = service.add_capital_movement(
        portfolio_id=1,
        movement_type="DEPOSIT",
        amount=Decimal("500"),
        movement_date=date(2026, 1, 3),
        movement_time=time(10, 0),
    )
    summary = service.get_portfolio_summary(1, price_map={10: Decimal("12")})

    assert movement.amount == Decimal("500")
    assert service.get_remaining_cash(1) == Decimal("1430")
    assert summary["net_capital"] == Decimal("1500")
    assert summary["total_value"] == Decimal("1526")
    assert summary["profit_loss"] == Decimal("26")


def test_model_portfolio_capital_withdraw_reduces_cash_and_net_capital():
    service = ModelPortfolioService(FakeModelPortfolioRepo(), FakeStockRepo())

    service.add_capital_movement(
        portfolio_id=1,
        movement_type="WITHDRAW",
        amount=Decimal("100"),
        movement_date=date(2026, 1, 3),
        movement_time=time(10, 0),
    )
    summary = service.get_portfolio_summary(1, price_map={10: Decimal("12")})

    assert service.get_remaining_cash(1) == Decimal("830")
    assert summary["net_capital"] == Decimal("900")
    assert summary["profit_loss"] == Decimal("26")


def test_model_portfolio_rejects_withdraw_above_cash():
    service = ModelPortfolioService(FakeModelPortfolioRepo(), FakeStockRepo())

    try:
        service.add_capital_movement(
            portfolio_id=1,
            movement_type="WITHDRAW",
            amount=Decimal("5000"),
            movement_date=date(2026, 1, 3),
            movement_time=time(10, 0),
        )
    except ValueError as exc:
        assert "Yetersiz nakit" in str(exc)
    else:
        raise AssertionError("Expected insufficient cash error")


def test_model_portfolio_deposit_allows_larger_later_buy():
    service = ModelPortfolioService(FakeModelPortfolioRepo(), FakeStockRepo())

    service.add_capital_movement(
        portfolio_id=1,
        movement_type="DEPOSIT",
        amount=Decimal("1000"),
        movement_date=date(2026, 1, 3),
        movement_time=time(9, 0),
    )
    trade = service.add_trade_by_ticker(
        portfolio_id=1,
        ticker="ASELS",
        side="BUY",
        quantity=100,
        price=Decimal("10"),
        trade_date=date(2026, 1, 3),
        trade_time=time(10, 0),
    )

    assert trade.quantity == 100
    assert service.get_remaining_cash(1) == Decimal("-70") + Decimal("1000")


def test_model_portfolio_rejects_retroactive_withdraw_that_breaks_later_buy():
    service = ModelPortfolioService(FakeModelPortfolioRepo(), FakeStockRepo())
    service.add_capital_movement(
        portfolio_id=1,
        movement_type="DEPOSIT",
        amount=Decimal("1000"),
        movement_date=date(2026, 1, 3),
        movement_time=time(9, 0),
    )
    service.add_trade_by_ticker(
        portfolio_id=1,
        ticker="ASELS",
        side="BUY",
        quantity=100,
        price=Decimal("10"),
        trade_date=date(2026, 1, 3),
        trade_time=time(10, 0),
    )

    try:
        service.add_capital_movement(
            portfolio_id=1,
            movement_type="WITHDRAW",
            amount=Decimal("950"),
            movement_date=date(2026, 1, 3),
            movement_time=time(9, 30),
        )
    except ValueError as exc:
        assert "sonraki model portf" in str(exc)
    else:
        raise AssertionError("Expected retroactive cash movement error")

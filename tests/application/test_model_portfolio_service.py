from datetime import date
from decimal import Decimal

from src.application.services.planning.model_portfolio_service import ModelPortfolioService
from src.domain.models.model_portfolio import ModelPortfolio, ModelPortfolioTrade
from src.domain.models.stock import Stock


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


def test_model_portfolio_service_computes_remaining_cash_and_summary():
    service = ModelPortfolioService(FakeModelPortfolioRepo(), FakeStockRepo())

    remaining_cash = service.get_remaining_cash(1)
    summary = service.get_portfolio_summary(1, price_map={10: Decimal("12")})

    assert remaining_cash == Decimal("930")
    assert summary["positions_value"] == Decimal("96")
    assert summary["total_value"] == Decimal("1026")
    assert summary["profit_loss"] == Decimal("26")


def test_model_portfolio_service_returns_positions_with_details():
    service = ModelPortfolioService(FakeModelPortfolioRepo(), FakeStockRepo())

    positions = service.get_positions_with_details(1, price_map={10: Decimal("12")})

    assert len(positions) == 1
    assert positions[0]["ticker"] == "ASELS.IS"
    assert positions[0]["quantity"] == 8
    assert positions[0]["current_value"] == Decimal("96")
    assert positions[0]["profit_loss"] == Decimal("16")


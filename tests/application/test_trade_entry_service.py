from datetime import date, time
from decimal import Decimal

from src.application.services.portfolio.trade_entry_service import TradeEntryService
from src.domain.models.stock import Stock
from src.domain.models.trade import TradeSide


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


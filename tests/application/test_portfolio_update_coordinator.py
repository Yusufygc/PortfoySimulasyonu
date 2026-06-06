from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from src.application.services.portfolio.portfolio_update_coordinator import PortfolioUpdateCoordinator
from src.domain.models.trade import Trade


class FakePortfolioRepo:
    def get_all_trades(self):
        return [
            Trade.create_buy(1, date(2026, 1, 1), 10, Decimal("10")),
            Trade.create_buy(2, date(2026, 1, 1), 100, Decimal("17.40")),
            Trade.create_sell(2, date(2026, 1, 2), 100, Decimal("17.41")),
        ]


class FakeStockRepo:
    def __init__(self):
        self.requested_ids = None

    def get_ticker_map_for_stock_ids(self, stock_ids):
        self.requested_ids = list(stock_ids)
        return {1: "AAA.IS"}


class FakePriceUpdateService:
    def __init__(self):
        self.stock_ticker_map = None
        self.price_date = None

    def last_completed_trading_day(self, today):
        return date(2026, 6, 5)

    def update_closing_prices_for_stocks(self, price_date, stock_ticker_map):
        self.price_date = price_date
        self.stock_ticker_map = dict(stock_ticker_map)
        return SimpleNamespace(prices={1: Decimal("12")})


class FakeReturnCalcService:
    def __init__(self):
        self.value_date = None

    def compute_portfolio_value_on(self, value_date):
        self.value_date = value_date
        return SimpleNamespace(as_of_date=value_date)


def test_update_today_prices_uses_only_active_positions():
    stock_repo = FakeStockRepo()
    price_update_service = FakePriceUpdateService()
    return_calc_service = FakeReturnCalcService()
    service = PortfolioUpdateCoordinator(
        portfolio_repo=FakePortfolioRepo(),
        stock_repo=stock_repo,
        price_update_service=price_update_service,
        return_calc_service=return_calc_service,
    )

    service.update_today_prices_and_get_snapshot()

    assert stock_repo.requested_ids == [1]
    assert price_update_service.price_date == date(2026, 6, 5)
    assert price_update_service.stock_ticker_map == {1: "AAA.IS"}
    assert return_calc_service.value_date == date(2026, 6, 5)

from datetime import date
from decimal import Decimal

from src.application.services.analysis.return_calc_service import ReturnCalcService
from src.domain.models.daily_price import DailyPrice
from src.domain.models.trade import Trade


class FakePortfolioRepo:
    def __init__(self, trades):
        self._trades = trades

    def get_all_trades(self):
        return list(self._trades)


class FakePriceRepo:
    def __init__(self, prices_for_date, latest_prices):
        self._prices_for_date = prices_for_date
        self._latest_prices = latest_prices

    def get_prices_for_date(self, price_date):
        return dict(self._prices_for_date.get(price_date, {}))

    def get_last_price_before(self, stock_id, price_date):
        point = self._latest_prices.get(stock_id)
        if point is None:
            return None
        point_date, price = point
        return DailyPrice(
            id=None,
            stock_id=stock_id,
            price_date=point_date,
            close_price=price,
        )


def test_compute_portfolio_value_uses_latest_price_when_value_date_is_missing():
    trades = [
        Trade.create_buy(
            stock_id=1,
            trade_date=date(2026, 4, 20),
            quantity=10,
            price=Decimal("10"),
        )
    ]
    service = ReturnCalcService(
        portfolio_repo=FakePortfolioRepo(trades),
        price_repo=FakePriceRepo(
            prices_for_date={date(2026, 4, 24): {}},
            latest_prices={1: (date(2026, 4, 23), Decimal("12"))},
        ),
    )

    snapshot = service.compute_portfolio_value_on(date(2026, 4, 24))

    assert snapshot.price_map == {1: Decimal("12")}
    assert snapshot.total_value == Decimal("120")
    assert snapshot.total_unrealized_pl == Decimal("20")


def test_compute_portfolio_value_keeps_exact_price_when_available():
    trades = [
        Trade.create_buy(
            stock_id=1,
            trade_date=date(2026, 4, 20),
            quantity=10,
            price=Decimal("10"),
        )
    ]
    service = ReturnCalcService(
        portfolio_repo=FakePortfolioRepo(trades),
        price_repo=FakePriceRepo(
            prices_for_date={date(2026, 4, 24): {1: Decimal("13")}},
            latest_prices={1: (date(2026, 4, 23), Decimal("12"))},
        ),
    )

    snapshot = service.compute_portfolio_value_on(date(2026, 4, 24))

    assert snapshot.price_map == {1: Decimal("13")}
    assert snapshot.total_value == Decimal("130")

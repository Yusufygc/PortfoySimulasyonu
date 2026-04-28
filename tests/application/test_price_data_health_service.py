from datetime import date
from decimal import Decimal

from src.application.services.market.price_data_health_service import PriceDataHealthService
from src.domain.models.daily_price import DailyPrice
from src.domain.models.model_portfolio import ModelPortfolio, ModelPortfolioTrade
from src.domain.models.stock import Stock
from src.domain.models.trade import Trade


class FakeStockRepo:
    def __init__(self, stocks):
        self._stocks = stocks

    def get_all_stocks(self):
        return list(self._stocks)

    def get_stock_by_id(self, stock_id):
        return next((stock for stock in self._stocks if stock.id == stock_id), None)


class FakePortfolioRepo:
    def __init__(self, trades):
        self._trades = trades

    def get_all_trades(self):
        return list(self._trades)


class FakeModelPortfolioRepo:
    def __init__(self, trades_by_portfolio=None):
        self._trades_by_portfolio = trades_by_portfolio or {}

    def get_all_model_portfolios(self):
        return [
            ModelPortfolio(id=portfolio_id, name=f"Model {portfolio_id}")
            for portfolio_id in self._trades_by_portfolio
        ]

    def get_trades_by_portfolio_id(self, portfolio_id):
        return list(self._trades_by_portfolio.get(portfolio_id, []))


class FakePriceRepo:
    def __init__(self, prices_by_stock):
        self.prices_by_stock = {
            stock_id: dict(points)
            for stock_id, points in prices_by_stock.items()
        }
        self.saved_prices = []

    def get_price_presence_map(self, stock_ids, start_date, end_date):
        return {
            stock_id: {
                point_date
                for point_date in self.prices_by_stock.get(stock_id, {})
                if start_date <= point_date <= end_date
            }
            for stock_id in stock_ids
        }

    def get_latest_price_dates(self, stock_ids):
        result = {}
        for stock_id in stock_ids:
            dates = sorted(self.prices_by_stock.get(stock_id, {}))
            if dates:
                result[stock_id] = dates[-1]
        return result

    def delete_prices_in_range(self, start_date, end_date):
        deleted = 0
        for points in self.prices_by_stock.values():
            for point_date in list(points):
                if start_date <= point_date <= end_date:
                    deleted += 1
                    del points[point_date]
        return deleted

    def upsert_daily_prices_bulk(self, prices):
        for daily_price in prices:
            self.saved_prices.append(daily_price)
            self.prices_by_stock.setdefault(daily_price.stock_id, {})[daily_price.price_date] = daily_price.close_price


class FakeMarketClient:
    def __init__(self, series_by_ticker, single_prices_by_ticker=None):
        self._series_by_ticker = series_by_ticker
        self._single_prices_by_ticker = single_prices_by_ticker or {}
        self.requests = []
        self.single_requests = []

    def get_price_series(self, ticker, start_date, end_date):
        self.requests.append((ticker, start_date, end_date))
        return {
            point_date: price
            for point_date, price in self._series_by_ticker.get(ticker, {}).items()
            if start_date <= point_date <= end_date
        }

    def get_closing_price(self, stock_id, ticker, price_date):
        self.single_requests.append((ticker, price_date))
        if price_date not in self._single_prices_by_ticker.get(ticker, {}):
            raise ValueError("fiyat verisi bulunamadi")
        return self._single_prices_by_ticker[ticker][price_date]


def make_service(
    prices_by_stock,
    series_by_ticker=None,
    trades=None,
    model_trades_by_portfolio=None,
    single_prices_by_ticker=None,
):
    stocks = [
        Stock(id=1, ticker="AAA.IS", name="AAA"),
        Stock(id=2, ticker="BBB.IS", name="BBB"),
    ]
    price_repo = FakePriceRepo(prices_by_stock)
    market_client = FakeMarketClient(series_by_ticker or {}, single_prices_by_ticker)
    service = PriceDataHealthService(
        stock_repo=FakeStockRepo(stocks),
        price_repo=price_repo,
        market_data_client=market_client,
        portfolio_repo=FakePortfolioRepo(trades or []) if trades is not None else None,
        model_portfolio_repo=(
            FakeModelPortfolioRepo(model_trades_by_portfolio)
            if model_trades_by_portfolio is not None
            else None
        ),
    )
    return service, price_repo, market_client


def test_weekends_are_not_counted_as_missing_days():
    service, _, _ = make_service(
        {
            1: {date(2026, 1, 2): Decimal("10"), date(2026, 1, 5): Decimal("11")},
            2: {date(2026, 1, 2): Decimal("20"), date(2026, 1, 5): Decimal("21")},
        }
    )

    report = service.analyze(date(2026, 1, 2), date(2026, 1, 5))

    assert [point.weekday() for point in report.weekend_days] == [5, 6]
    assert report.total_missing_count == 0
    assert report.holiday_candidate_count == 0


def test_empty_weekday_for_all_stocks_is_holiday_candidate_not_stock_missing():
    service, _, _ = make_service(
        {
            1: {date(2026, 1, 2): Decimal("10")},
            2: {date(2026, 1, 2): Decimal("20")},
        }
    )

    report = service.analyze(date(2026, 1, 2), date(2026, 1, 5))

    assert report.holiday_candidate_dates == [date(2026, 1, 5)]
    assert report.total_missing_count == 0


def test_partial_weekday_gap_is_stock_level_missing_data():
    service, _, _ = make_service(
        {
            1: {date(2026, 1, 2): Decimal("10"), date(2026, 1, 5): Decimal("11")},
            2: {date(2026, 1, 2): Decimal("20")},
        }
    )

    report = service.analyze(date(2026, 1, 2), date(2026, 1, 5))

    row = next(item for item in report.rows if item.stock_id == 2)
    assert row.missing_dates == [date(2026, 1, 5)]
    assert report.holiday_candidate_dates == []
    assert report.total_missing_count == 1


def test_update_from_latest_to_today_uses_each_stocks_latest_price_date():
    service, price_repo, market_client = make_service(
        {
            1: {date(2026, 1, 2): Decimal("10")},
            2: {date(2026, 1, 1): Decimal("20")},
        },
        {
            "AAA.IS": {date(2026, 1, 5): Decimal("12")},
            "BBB.IS": {date(2026, 1, 5): Decimal("22")},
        },
    )

    result = service.update_from_latest_to_today(today=date(2026, 1, 5))

    assert result.updated_count == 2
    assert {item.stock_id for item in price_repo.saved_prices} == {1, 2}
    assert {item.price_date for item in price_repo.saved_prices} == {date(2026, 1, 5)}
    assert market_client.requests == [
        ("AAA.IS", date(2026, 1, 3), date(2026, 1, 5)),
        ("BBB.IS", date(2026, 1, 2), date(2026, 1, 5)),
    ]


def test_empty_market_series_does_not_crash_update():
    service, price_repo, _ = make_service(
        {1: {date(2026, 1, 2): Decimal("10")}, 2: {date(2026, 1, 2): Decimal("20")}},
        {},
    )

    result = service.update_stock_range(1, date(2026, 1, 5), date(2026, 1, 5))

    assert result.updated_count == 0
    assert "AAA.IS" in result.errors[0]
    assert price_repo.saved_prices == []


def test_empty_market_series_falls_back_to_single_day_closing_prices():
    service, price_repo, market_client = make_service(
        {1: {}, 2: {}},
        {},
        single_prices_by_ticker={
            "AAA.IS": {date(2026, 1, 5): Decimal("12")},
        },
    )

    result = service.update_stock_range(1, date(2026, 1, 5), date(2026, 1, 5))

    assert result.updated_count == 1
    assert price_repo.prices_by_stock[1][date(2026, 1, 5)] == Decimal("12")
    assert market_client.requests == [("AAA.IS", date(2026, 1, 5), date(2026, 1, 5))]
    assert market_client.single_requests == [("AAA.IS", date(2026, 1, 5))]


def test_dates_before_stock_first_trade_are_not_counted_as_missing():
    service, _, _ = make_service(
        {
            1: {date(2026, 1, 5): Decimal("10")},
            2: {date(2026, 1, 2): Decimal("20"), date(2026, 1, 5): Decimal("21")},
        },
        trades=[
            Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 5), quantity=1, price=Decimal("10")),
            Trade.create_buy(stock_id=2, trade_date=date(2026, 1, 2), quantity=1, price=Decimal("20")),
        ],
    )

    report = service.analyze(date(2026, 1, 2), date(2026, 1, 5))

    row = next(item for item in report.rows if item.stock_id == 1)
    assert row.first_trade_date == date(2026, 1, 5)
    assert row.missing_dates == []
    assert report.total_missing_count == 0


def test_stocks_without_dashboard_or_model_trades_are_not_scanned_when_repos_are_available():
    service, _, _ = make_service(
        {
            1: {date(2026, 1, 2): Decimal("10")},
            2: {},
        },
        trades=[
            Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 2), quantity=1, price=Decimal("10")),
        ],
        model_trades_by_portfolio={},
    )

    report = service.analyze(date(2026, 1, 2), date(2026, 1, 5))

    assert report.total_stock_count == 1
    assert [row.stock_id for row in report.rows] == [1]


def test_model_portfolio_stocks_are_scanned_and_stored_like_dashboard_stocks():
    model_trade = ModelPortfolioTrade.create_buy(
        portfolio_id=4,
        stock_id=2,
        trade_date=date(2026, 1, 2),
        quantity=1,
        price=Decimal("20"),
    )
    service, price_repo, market_client = make_service(
        {
            1: {date(2026, 1, 2): Decimal("10")},
            2: {},
        },
        {
            "BBB.IS": {date(2026, 1, 2): Decimal("22")},
        },
        trades=[
            Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 2), quantity=1, price=Decimal("10")),
        ],
        model_trades_by_portfolio={4: [model_trade]},
    )

    report = service.analyze(date(2026, 1, 2), date(2026, 1, 5))
    result = service.update_missing_prices(date(2026, 1, 2), date(2026, 1, 5), stock_ids=[2])

    assert {row.stock_id for row in report.rows} == {1, 2}
    assert result.updated_count == 1
    assert price_repo.prices_by_stock[2][date(2026, 1, 2)] == Decimal("22")
    assert market_client.requests == [("BBB.IS", date(2026, 1, 2), date(2026, 1, 2))]

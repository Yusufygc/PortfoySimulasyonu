from datetime import date
from decimal import Decimal

import pytest

from src.application.services.analysis import AnalysisFilterState, AnalysisService
from src.domain.models.daily_price import DailyPrice
from src.domain.models.stock import Stock
from src.domain.models.trade import Trade


class FakePortfolioRepo:
    def __init__(self, trades):
        self._trades = trades

    def get_all_trades(self):
        return list(self._trades)


class FakePriceRepo:
    def __init__(self, prices_by_stock):
        self._prices_by_stock = prices_by_stock

    def get_price_series(self, stock_id, start_date, end_date):
        return [
            DailyPrice(id=None, stock_id=stock_id, price_date=point_date, close_price=price)
            for point_date, price in self._prices_by_stock.get(stock_id, {}).items()
            if start_date <= point_date <= end_date
        ]

    def get_last_price_before(self, stock_id, price_date):
        eligible = [
            (point_date, price)
            for point_date, price in self._prices_by_stock.get(stock_id, {}).items()
            if point_date < price_date
        ]
        if not eligible:
            return None
        last_date, last_price = sorted(eligible)[-1]
        return DailyPrice(id=None, stock_id=stock_id, price_date=last_date, close_price=last_price)


class FakeStockRepo:
    def __init__(self, stocks):
        self._stocks = stocks

    def get_all_stocks(self):
        return list(self._stocks)

    def get_ticker_map_for_stock_ids(self, stock_ids):
        return {stock.id: stock.ticker for stock in self._stocks if stock.id in stock_ids}


class FakeMarketDataClient:
    def __init__(self, series_map):
        self._series_map = series_map
        self.requested_tickers = []

    def get_price_series(self, ticker, start_date, end_date):
        self.requested_tickers.append(ticker)
        series = self._series_map.get(ticker, {})
        return {
            point_date: value
            for point_date, value in series.items()
            if start_date <= point_date <= end_date
        }


@pytest.fixture
def analysis_service():
    trades = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=10, price=Decimal("100")),
        Trade.create_buy(stock_id=2, trade_date=date(2026, 1, 1), quantity=5, price=Decimal("20")),
    ]
    prices = {
        1: {
            date(2026, 1, 1): Decimal("100"),
            date(2026, 1, 2): Decimal("110"),
            date(2026, 1, 3): Decimal("120"),
        },
        2: {
            date(2026, 1, 1): Decimal("20"),
            date(2026, 1, 2): Decimal("18"),
            date(2026, 1, 3): Decimal("19"),
        },
    }
    stocks = [
        Stock(id=1, ticker="AKBNK"),
        Stock(id=2, ticker="ASELS"),
    ]
    benchmark_series = {
        "XU100.IS": {
            date(2026, 1, 1): Decimal("100"),
            date(2026, 1, 2): Decimal("101"),
            date(2026, 1, 3): Decimal("102"),
        },
        "GC=F": {
            date(2026, 1, 1): Decimal("100"),
            date(2026, 1, 2): Decimal("99"),
            date(2026, 1, 3): Decimal("101"),
        },
        "TRY=X": {
            date(2026, 1, 1): Decimal("100"),
            date(2026, 1, 2): Decimal("101"),
            date(2026, 1, 3): Decimal("103"),
        },
    }
    return AnalysisService(
        portfolio_repo=FakePortfolioRepo(trades),
        price_repo=FakePriceRepo(prices),
        stock_repo=FakeStockRepo(stocks),
        market_data_client=FakeMarketDataClient(benchmark_series),
    )


def test_overview_returns_expected_high_level_metrics(analysis_service):
    filter_state = AnalysisFilterState(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
        selected_stock_ids=[],
        selected_benchmarks=["bist100"],
        portfolio_source="dashboard",
    )

    overview = analysis_service.get_overview(filter_state)

    assert overview.total_value == Decimal("1295")
    assert overview.period_return_pct is not None
    assert overview.period_return_pct > 17
    assert overview.benchmark_gap_pct is not None
    assert overview.largest_position_label == "AKBNK"
    assert overview.best_contributor_label == "AKBNK"
    assert overview.worst_contributor_label == "ASELS"
    assert overview.warnings == []


def test_comparison_view_builds_deposit_benchmark_series(monkeypatch, analysis_service):
    monkeypatch.setenv("ANALYSIS_DEPOSIT_ANNUAL_RATE", "0.36")
    filter_state = AnalysisFilterState(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
        selected_stock_ids=[],
        selected_benchmarks=["deposit"],
        portfolio_source="dashboard",
    )

    comparison = analysis_service.get_comparison_view(filter_state, ["deposit"])

    assert len(comparison.benchmark_series) == 1
    deposit_series = comparison.benchmark_series[0]
    values = list(deposit_series.points.values())
    assert deposit_series.code == "deposit"
    assert len(values) == 3
    assert values[1] > values[0]
    assert values[2] > values[1]


def test_missing_price_data_creates_warning():
    trades = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=10, price=Decimal("100")),
    ]
    service = AnalysisService(
        portfolio_repo=FakePortfolioRepo(trades),
        price_repo=FakePriceRepo({1: {}}),
        stock_repo=FakeStockRepo([Stock(id=1, ticker="AKBNK")]),
        market_data_client=FakeMarketDataClient({}),
    )
    filter_state = AnalysisFilterState(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
        selected_stock_ids=[],
        selected_benchmarks=["bist100"],
        portfolio_source="dashboard",
    )

    risk_view = service.get_allocation_risk_view(filter_state)

    assert any("AKBNK" in warning for warning in risk_view.warnings)


def test_market_benchmark_falls_back_to_secondary_ticker():
    trades = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=10, price=Decimal("100")),
    ]
    market_client = FakeMarketDataClient(
        {
            "^XU100": {
                date(2026, 1, 1): Decimal("100"),
                date(2026, 1, 2): Decimal("101"),
                date(2026, 1, 3): Decimal("102"),
            }
        }
    )
    service = AnalysisService(
        portfolio_repo=FakePortfolioRepo(trades),
        price_repo=FakePriceRepo({1: {
            date(2026, 1, 1): Decimal("100"),
            date(2026, 1, 2): Decimal("105"),
            date(2026, 1, 3): Decimal("110"),
        }}),
        stock_repo=FakeStockRepo([Stock(id=1, ticker="AKBNK")]),
        market_data_client=market_client,
    )
    filter_state = AnalysisFilterState(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
        selected_benchmarks=["bist100"],
        portfolio_source="dashboard",
    )

    overview = service.get_overview(filter_state)

    assert overview.benchmark_gap_pct is not None
    assert market_client.requested_tickers[:2] == ["XU100.IS", "^XU100"]
    assert not any("BIST 100" in warning for warning in overview.warnings)


def test_gold_benchmark_can_be_composed_from_gold_and_usd_series():
    trades = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=10, price=Decimal("100")),
    ]
    market_client = FakeMarketDataClient(
        {
            "XAUUSD=X": {
                date(2026, 1, 1): Decimal("100"),
                date(2026, 1, 2): Decimal("102"),
                date(2026, 1, 3): Decimal("104"),
            },
            "TRY=X": {
                date(2026, 1, 1): Decimal("30"),
                date(2026, 1, 2): Decimal("31"),
                date(2026, 1, 3): Decimal("32"),
            },
        }
    )
    service = AnalysisService(
        portfolio_repo=FakePortfolioRepo(trades),
        price_repo=FakePriceRepo({1: {
            date(2026, 1, 1): Decimal("100"),
            date(2026, 1, 2): Decimal("105"),
            date(2026, 1, 3): Decimal("110"),
        }}),
        stock_repo=FakeStockRepo([Stock(id=1, ticker="AKBNK")]),
        market_data_client=market_client,
    )
    filter_state = AnalysisFilterState(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
        selected_benchmarks=["gold"],
        portfolio_source="dashboard",
    )

    comparison = service.get_comparison_view(filter_state, ["gold"])

    assert len(comparison.benchmark_series) == 1
    gold_series = comparison.benchmark_series[0].points
    assert list(gold_series.values()) == [Decimal("3000"), Decimal("3162"), Decimal("3328")]
    assert market_client.requested_tickers[:3] == ["XAUTRY=X", "XAUUSD=X", "TRY=X"]


def test_invalid_date_range_raises_value_error(analysis_service):
    filter_state = AnalysisFilterState(
        start_date=date(2026, 1, 5),
        end_date=date(2026, 1, 3),
    )

    with pytest.raises(ValueError):
        analysis_service.get_overview(filter_state)

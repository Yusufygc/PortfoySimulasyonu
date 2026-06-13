from datetime import date
from decimal import Decimal

import pytest

from src.application.services.analysis import AnalysisFilterState, AnalysisService
from src.domain.models.cash_movement import CashMovement
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


class FakeCashMovementRepo:
    def __init__(self, movements):
        self._movements = movements

    def get_all_movements(self):
        return list(self._movements)


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
        "TCMB_TRY_DEPOSIT_3M": {
            date(2026, 1, 1): Decimal("36"),
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
    assert len(overview.warnings) == 1
    assert "Forward Fill" in overview.warnings[0]


def test_comparison_view_builds_deposit_benchmark_series(analysis_service):
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
    assert values[0] == Decimal("100")
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


def test_sold_dashboard_stock_is_not_exposed_as_active_analysis_stock():
    trades = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=10, price=Decimal("10")),
        Trade.create_sell(stock_id=1, trade_date=date(2026, 1, 2), quantity=10, price=Decimal("11")),
        Trade.create_buy(stock_id=2, trade_date=date(2026, 1, 3), quantity=5, price=Decimal("20")),
    ]
    service = AnalysisService(
        portfolio_repo=FakePortfolioRepo(trades),
        price_repo=FakePriceRepo({2: {date(2026, 1, 3): Decimal("21")}}),
        stock_repo=FakeStockRepo([Stock(id=1, ticker="BORSK.IS"), Stock(id=2, ticker="AKBNK.IS")]),
        market_data_client=FakeMarketDataClient({}),
    )

    stock_map = service.get_stock_map_for_source("dashboard")

    assert stock_map == {2: "AKBNK.IS"}


def test_sold_stock_without_prices_does_not_create_analysis_warning():
    trades = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=10, price=Decimal("10")),
        Trade.create_sell(stock_id=1, trade_date=date(2026, 1, 2), quantity=10, price=Decimal("11")),
        Trade.create_buy(stock_id=2, trade_date=date(2026, 1, 3), quantity=5, price=Decimal("20")),
    ]
    service = AnalysisService(
        portfolio_repo=FakePortfolioRepo(trades),
        price_repo=FakePriceRepo({2: {date(2026, 1, 3): Decimal("21")}}),
        stock_repo=FakeStockRepo([Stock(id=1, ticker="BORSK.IS"), Stock(id=2, ticker="AKBNK.IS")]),
        market_data_client=FakeMarketDataClient({}),
    )
    filter_state = AnalysisFilterState(
        start_date=date(2026, 1, 3),
        end_date=date(2026, 1, 4),
        selected_stock_ids=[],
        selected_benchmarks=[],
        portfolio_source="dashboard",
    )

    payload = service.get_page_payload(filter_state)

    assert not any("BORSK" in warning for warning in payload["overview"].warnings)
    assert payload["overview"].largest_position_label == "AKBNK"


def test_dashboard_analysis_total_value_keeps_cash_from_closed_trade():
    trades = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=10, price=Decimal("10")),
        Trade.create_sell(stock_id=1, trade_date=date(2026, 1, 2), quantity=10, price=Decimal("11")),
    ]
    service = AnalysisService(
        portfolio_repo=FakePortfolioRepo(trades),
        price_repo=FakePriceRepo({}),
        stock_repo=FakeStockRepo([Stock(id=1, ticker="BORSK.IS")]),
        market_data_client=FakeMarketDataClient({}),
        cash_movement_repo=FakeCashMovementRepo(
            [CashMovement.create_deposit(amount=Decimal("100"), movement_date=date(2026, 1, 1))]
        ),
    )
    filter_state = AnalysisFilterState(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
        selected_stock_ids=[],
        selected_benchmarks=[],
        portfolio_source="dashboard",
    )

    overview = service.get_overview(filter_state)

    assert overview.total_value == Decimal("110")


def test_stock_sold_inside_analysis_range_is_valued_until_closed():
    trades = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=10, price=Decimal("10")),
        Trade.create_sell(stock_id=1, trade_date=date(2026, 1, 3), quantity=10, price=Decimal("12")),
    ]
    service = AnalysisService(
        portfolio_repo=FakePortfolioRepo(trades),
        price_repo=FakePriceRepo({1: {date(2026, 1, 1): Decimal("10"), date(2026, 1, 2): Decimal("11"), date(2026, 1, 3): Decimal("12")}}),
        stock_repo=FakeStockRepo([Stock(id=1, ticker="BORSK.IS")]),
        market_data_client=FakeMarketDataClient({}),
        cash_movement_repo=FakeCashMovementRepo(
            [CashMovement.create_deposit(amount=Decimal("100"), movement_date=date(2026, 1, 1))]
        ),
    )
    filter_state = AnalysisFilterState(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
        selected_stock_ids=[],
        selected_benchmarks=[],
        portfolio_source="dashboard",
    )

    overview = service.get_overview(filter_state)

    assert overview.total_value == Decimal("120")
    assert not any("BORSK" in warning for warning in overview.warnings)


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
    expected = [
        Decimal("3000") / Decimal("31.1034768"),
        Decimal("3162") / Decimal("31.1034768"),
        Decimal("3328") / Decimal("31.1034768"),
    ]
    assert [float(value) for value in gold_series.values()] == pytest.approx([float(value) for value in expected])
    assert market_client.requested_tickers[:3] == ["XAUTRY=X", "XAUUSD=X", "TRY=X"]


def test_gold_benchmark_converts_direct_xautry_ounce_value_to_gram():
    trades = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=10, price=Decimal("100")),
    ]
    market_client = FakeMarketDataClient(
        {
            "XAUTRY=X": {
                date(2026, 1, 1): Decimal("31000"),
                date(2026, 1, 2): Decimal("31100"),
            },
        }
    )
    service = AnalysisService(
        portfolio_repo=FakePortfolioRepo(trades),
        price_repo=FakePriceRepo({1: {
            date(2026, 1, 1): Decimal("100"),
            date(2026, 1, 2): Decimal("105"),
        }}),
        stock_repo=FakeStockRepo([Stock(id=1, ticker="AKBNK")]),
        market_data_client=market_client,
    )
    filter_state = AnalysisFilterState(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        selected_benchmarks=["gold"],
        portfolio_source="dashboard",
    )

    comparison = service.get_comparison_view(filter_state, ["gold"])

    values = list(comparison.benchmark_series[0].points.values())
    assert [float(value) for value in values] == pytest.approx([
        float(Decimal("31000") / Decimal("31.1034768")),
        float(Decimal("31100") / Decimal("31.1034768")),
    ])
    assert market_client.requested_tickers == ["XAUTRY=X"]


def test_deposit_benchmark_warns_when_real_rate_data_missing():
    trades = [
        Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 1), quantity=10, price=Decimal("100")),
    ]
    service = AnalysisService(
        portfolio_repo=FakePortfolioRepo(trades),
        price_repo=FakePriceRepo({1: {
            date(2026, 1, 1): Decimal("100"),
            date(2026, 1, 2): Decimal("105"),
            date(2026, 1, 3): Decimal("110"),
        }}),
        stock_repo=FakeStockRepo([Stock(id=1, ticker="AKBNK")]),
        market_data_client=FakeMarketDataClient({}),
    )
    filter_state = AnalysisFilterState(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
        selected_benchmarks=["deposit"],
        portfolio_source="dashboard",
    )

    comparison = service.get_comparison_view(filter_state, ["deposit"])

    assert comparison.benchmark_series == []
    assert any("Mevduat Faizi" in warning for warning in comparison.warnings)


def test_invalid_date_range_raises_value_error(analysis_service):
    filter_state = AnalysisFilterState(
        start_date=date(2026, 1, 5),
        end_date=date(2026, 1, 3),
    )

    with pytest.raises(ValueError):
        analysis_service.get_overview(filter_state)


def test_page_payload_contains_all_sections(analysis_service):
    filter_state = AnalysisFilterState(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
        selected_stock_ids=[],
        selected_benchmarks=["bist100"],
        portfolio_source="dashboard",
    )

    payload = analysis_service.get_page_payload(filter_state)

    assert set(payload.keys()) == {"overview", "comparison", "risk"}


def test_overview_risk_payload_skips_comparison_section(analysis_service, monkeypatch):
    filter_state = AnalysisFilterState(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
        selected_stock_ids=[],
        selected_benchmarks=["bist100"],
        portfolio_source="dashboard",
    )

    monkeypatch.setattr(
        analysis_service,
        "get_comparison_view",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("comparison should not be built")),
    )

    payload = analysis_service.get_overview_risk_payload(filter_state)

    assert set(payload.keys()) == {"overview", "risk"}


def test_empty_benchmark_selection_disables_benchmark_series(analysis_service):
    filter_state = AnalysisFilterState(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
        selected_stock_ids=[],
        selected_benchmarks=[],
        portfolio_source="dashboard",
    )

    comparison = analysis_service.get_comparison_view(filter_state)
    overview = analysis_service.get_overview(filter_state)

    assert comparison.benchmark_series == []
    assert comparison.comparison_metrics == []
    assert overview.benchmark_gap_pct is None


def test_comparison_view_with_other_portfolios(analysis_service):
    class FakeModelPortfolio:
        def __init__(self, id, name):
            self.id = id
            self.name = name

    class FakeModelTrade:
        def __init__(self, stock_id, trade_date, quantity, price, side):
            self.stock_id = stock_id
            self.trade_date = trade_date
            self.quantity = quantity
            self.price = price
            self.side = side
            self.trade_time = None

    class FakeModelPortfolioService:
        def get_all_portfolios(self):
            return [FakeModelPortfolio(4, "Model Portfoy 4")]
        def get_portfolio_trades(self, portfolio_id):
            from src.domain.models.model_portfolio import ModelTradeSide
            return [
                FakeModelTrade(1, date(2026, 1, 1), 10, Decimal("100"), ModelTradeSide.BUY)
            ]

    analysis_service._source_resolver._model_portfolio_service = FakeModelPortfolioService()

    filter_state = AnalysisFilterState(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
        selected_stock_ids=[],
        selected_benchmarks=[],
        portfolio_source="dashboard",
        comparison_portfolio_sources=["dashboard", "model:4"],
    )

    comparison = analysis_service.get_comparison_view(filter_state)

    assert len(comparison.comparison_portfolios) == 1
    p4_series = comparison.comparison_portfolios[0]
    assert p4_series.code == "model:4"
    assert p4_series.label == "Model Portfoy 4"
    assert len(p4_series.points) == 3


def test_closed_model_position_is_not_exposed_as_active_analysis_stock(analysis_service):
    from src.domain.models.model_portfolio import ModelTradeSide

    class FakeModelPortfolio:
        def __init__(self, id, name):
            self.id = id
            self.name = name

    class FakeModelTrade:
        def __init__(self, stock_id, trade_date, quantity, price, side):
            self.stock_id = stock_id
            self.trade_date = trade_date
            self.quantity = quantity
            self.price = price
            self.side = side
            self.trade_time = None

    class FakeModelPortfolioService:
        def get_all_portfolios(self):
            return [FakeModelPortfolio(4, "Model Portfoy 4")]

        def get_positions(self, portfolio_id):
            return {1: 10}

        def get_portfolio_trades(self, portfolio_id):
            return [
                FakeModelTrade(1, date(2026, 1, 1), 10, Decimal("100"), ModelTradeSide.BUY),
                FakeModelTrade(2, date(2026, 1, 1), 5, Decimal("20"), ModelTradeSide.BUY),
                FakeModelTrade(2, date(2026, 1, 2), 5, Decimal("22"), ModelTradeSide.SELL),
            ]

    analysis_service._source_resolver._model_portfolio_service = FakeModelPortfolioService()

    stock_map = analysis_service.get_stock_map_for_source("model:4")

    assert stock_map == {1: "AKBNK"}


def test_stale_model_source_is_normalized_without_duplicate_comparison(analysis_service):
    class FakeModelPortfolioService:
        def get_all_portfolios(self):
            return []

        def get_portfolio_trades(self, portfolio_id):
            raise AssertionError("stale model trades should not be loaded")

    analysis_service._source_resolver._model_portfolio_service = FakeModelPortfolioService()
    filter_state = AnalysisFilterState(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
        selected_stock_ids=[],
        selected_benchmarks=[],
        portfolio_source="model:99",
        comparison_portfolio_sources=["model:99"],
    )

    comparison = analysis_service.get_comparison_view(filter_state)
    overview = analysis_service.get_overview(filter_state)

    assert comparison.current_portfolio_label == "Ana Portfoy"
    assert comparison.comparison_portfolios == []
    assert overview.portfolio_label == "Ana Portfoy"

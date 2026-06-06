from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")
from PyQt5.QtWidgets import QWidget

from src.domain.models.portfolio import Portfolio
from src.domain.models.trade import Trade
from src.ui.pages.dashboard.dashboard_presenter import DashboardPresenter


class SummaryCardsSpy:
    def __init__(self):
        self.base_metrics = None

    def update_base_metrics(self, total_value, total_cost, capital, profit_loss):
        self.base_metrics = (total_value, total_cost, capital, profit_loss)


class PortfolioTableSpy:
    def __init__(self):
        self.model = None
        self.summary = None

    def set_model(self, model):
        self.model = model

    def update_summary_row(self, total_value, profit_loss):
        self.summary = (total_value, profit_loss)


class DummySignal:
    def connect(self, *_args, **_kwargs):
        return None


def test_prices_updated_event_uses_active_positions_and_numeric_total_cost():
    portfolio = Portfolio.from_trades(
        [
            Trade.create_buy(1, date(2026, 1, 1), 10, Decimal("10")),
            Trade.create_buy(2, date(2026, 1, 1), 100, Decimal("17.40")),
            Trade.create_sell(2, date(2026, 1, 2), 100, Decimal("17.41")),
        ]
    )
    summary_cards = SummaryCardsSpy()
    table = PortfolioTableSpy()
    page = SimpleNamespace(
        portfolio_model=SimpleNamespace(_price_map={1: Decimal("12"), 2: Decimal("99")}),
        portfolio_service=SimpleNamespace(get_current_portfolio=lambda: portfolio),
        summary_cards=summary_cards,
        portfolio_table_widget=table,
        _capital=Decimal("50"),
        _is_refreshing=False,
    )

    DashboardPresenter(page).on_prices_updated_event({1: Decimal("12"), 2: Decimal("99")})

    assert summary_cards.base_metrics == (
        Decimal("170"),
        Decimal("100"),
        Decimal("50"),
        Decimal("20"),
    )
    assert table.summary == (Decimal("170"), Decimal("20"))


def test_refresh_data_builds_previous_close_map_and_sets_table_model(qapp, monkeypatch):
    portfolio = Portfolio.from_trades([Trade.create_buy(1, date(2026, 1, 1), 10, Decimal("10"))])
    summary_cards = SummaryCardsSpy()
    table = PortfolioTableSpy()
    page = QWidget()
    page.portfolio_model = None
    page.portfolio_service = SimpleNamespace(
        get_current_portfolio=lambda: portfolio,
        get_cash_balance=lambda: Decimal("30"),
        get_portfolio_health=lambda: SimpleNamespace(invalid_trades=[]),
    )
    page.return_calc_service = SimpleNamespace(
        compute_portfolio_value_on=lambda _today: SimpleNamespace(
            price_map={1: Decimal("12")},
            total_value=Decimal("120"),
            total_unrealized_pl=Decimal("20"),
        )
    )
    page.stock_repo = SimpleNamespace(get_ticker_map_for_stock_ids=lambda ids: {1: "ASELS.IS"} if ids else {})
    page.price_repo = SimpleNamespace(
        get_last_price_before=lambda stock_id, point_date: (
            SimpleNamespace(close_price=Decimal("11"))
            if stock_id == 1 and point_date == date(2026, 6, 4)
            else None
        )
    )
    page.summary_cards = summary_cards
    page.portfolio_table_widget = table
    page.container = SimpleNamespace(event_bus=SimpleNamespace(prices_updated=DummySignal()))
    page._capital = Decimal("0")
    page._is_refreshing = False
    page._last_invalid_trade_warning_count = 0
    monkeypatch.setattr("src.ui.pages.dashboard.dashboard_presenter.date", SimpleNamespace(today=lambda: date(2026, 6, 5)))

    DashboardPresenter(page).refresh_data()

    assert page.portfolio_model is table.model
    assert page.portfolio_model._previous_close_map == {1: Decimal("11")}
    assert page.portfolio_model._ticker_map == {1: "ASELS.IS"}
    assert summary_cards.base_metrics == (
        Decimal("150"),
        Decimal("100"),
        Decimal("30"),
        Decimal("20"),
    )
    assert table.summary == (Decimal("150"), Decimal("20"))


def test_refresh_data_prefers_latest_price_for_current_valuation(qapp, monkeypatch):
    portfolio = Portfolio.from_trades([Trade.create_buy(1, date(2026, 1, 1), 10, Decimal("10"))])
    summary_cards = SummaryCardsSpy()
    table = PortfolioTableSpy()
    page = QWidget()
    page.portfolio_model = None
    page.portfolio_service = SimpleNamespace(
        get_current_portfolio=lambda: portfolio,
        get_cash_balance=lambda: Decimal("30"),
        get_portfolio_health=lambda: SimpleNamespace(invalid_trades=[]),
    )
    page.return_calc_service = SimpleNamespace(
        compute_portfolio_value_on=lambda _today: SimpleNamespace(
            price_map={1: Decimal("12")},
            total_value=Decimal("120"),
            total_unrealized_pl=Decimal("20"),
        )
    )
    page.latest_price_repo = SimpleNamespace(get_latest_price_map=lambda stock_ids: {1: Decimal("13")})
    page.stock_repo = SimpleNamespace(get_ticker_map_for_stock_ids=lambda ids: {1: "ASELS.IS"} if ids else {})
    page.price_repo = SimpleNamespace(get_last_price_before=lambda *_args, **_kwargs: None)
    page.summary_cards = summary_cards
    page.portfolio_table_widget = table
    page.container = SimpleNamespace(event_bus=SimpleNamespace(prices_updated=DummySignal()))
    page._capital = Decimal("0")
    page._is_refreshing = False
    page._last_invalid_trade_warning_count = 0
    monkeypatch.setattr("src.ui.pages.dashboard.dashboard_presenter.date", SimpleNamespace(today=lambda: date(2026, 6, 5)))

    DashboardPresenter(page).refresh_data()

    assert page.portfolio_model._price_map == {1: Decimal("13")}
    assert summary_cards.base_metrics == (
        Decimal("160"),
        Decimal("100"),
        Decimal("30"),
        Decimal("30"),
    )
    assert table.summary == (Decimal("160"), Decimal("30"))


def test_refresh_data_leaves_daily_change_empty_without_previous_close(qapp, monkeypatch):
    portfolio = Portfolio.from_trades([Trade.create_buy(1, date(2026, 1, 1), 10, Decimal("10"))])
    table = PortfolioTableSpy()
    page = QWidget()
    page.portfolio_model = None
    page.portfolio_service = SimpleNamespace(
        get_current_portfolio=lambda: portfolio,
        get_cash_balance=lambda: Decimal("0"),
        get_portfolio_health=lambda: SimpleNamespace(invalid_trades=[]),
    )
    page.return_calc_service = SimpleNamespace(
        compute_portfolio_value_on=lambda _today: SimpleNamespace(
            price_map={1: Decimal("12")},
            total_value=Decimal("120"),
            total_unrealized_pl=Decimal("20"),
        )
    )
    page.stock_repo = SimpleNamespace(get_ticker_map_for_stock_ids=lambda ids: {1: "ASELS.IS"} if ids else {})
    page.price_repo = SimpleNamespace(get_last_price_before=lambda *_args, **_kwargs: None)
    page.summary_cards = SummaryCardsSpy()
    page.portfolio_table_widget = table
    page.container = SimpleNamespace(event_bus=SimpleNamespace(prices_updated=DummySignal()))
    page._capital = Decimal("0")
    page._is_refreshing = False
    page._last_invalid_trade_warning_count = 0
    monkeypatch.setattr("src.ui.pages.dashboard.dashboard_presenter.date", SimpleNamespace(today=lambda: date(2026, 6, 5)))

    DashboardPresenter(page).refresh_data()

    daily_change_index = page.portfolio_model.index(0, 3)
    assert page.portfolio_model._previous_close_map == {}
    assert page.portfolio_model.data(daily_change_index) == "-"

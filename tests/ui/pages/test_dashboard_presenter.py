from datetime import date
from decimal import Decimal
from types import SimpleNamespace

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
        self.summary = None

    def update_summary_row(self, total_value, profit_loss):
        self.summary = (total_value, profit_loss)


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

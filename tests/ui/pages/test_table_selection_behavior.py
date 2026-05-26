import sys
from decimal import Decimal
from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QTableView, QTableWidget

from src.domain.models.position import Position
from src.ui.pages.dashboard.dashboard_portfolio_table import DashboardPortfolioTable
from src.ui.pages.watchlist_page import WatchlistPage
from src.ui.portfolio_table_model import PortfolioTableModel
from src.ui.widgets.model_portfolio.tables.positions_table import PositionsTable
from src.ui.widgets.optimization.tables.suggestions_table import SuggestionsTable


app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


def _assert_passive_table(table: QTableWidget) -> None:
    assert table.selectionMode() == QTableWidget.NoSelection
    assert table.editTriggers() == QTableWidget.NoEditTriggers
    assert table.focusPolicy() == Qt.NoFocus


def test_model_positions_table_is_passive_and_preserves_colored_profit_loss():
    table = PositionsTable()
    table.populate(
        [
            {
                "ticker": "ASELS.IS",
                "quantity": 10,
                "avg_cost": Decimal("20"),
                "current_price": Decimal("25"),
                "current_value": Decimal("250"),
                "profit_loss": Decimal("50"),
            }
        ]
    )

    _assert_passive_table(table)
    pl_item = table.item(0, 5)
    assert not pl_item.flags() & Qt.ItemIsSelectable
    assert pl_item.foreground().color().name() == "#00ff00"


def test_optimization_suggestions_table_is_passive_and_keeps_action_color():
    table = SuggestionsTable()
    table.populate(
        [
            SimpleNamespace(
                symbol="ASELS.IS",
                current_weight=10.0,
                optimal_weight=15.0,
                change=5.0,
                action="EKLE",
            )
        ]
    )

    _assert_passive_table(table)
    action_item = table.item(0, 4)
    assert not action_item.flags() & Qt.ItemIsSelectable
    assert action_item.foreground().color().name() == "#00ff00"


def test_watchlist_stock_table_is_passive():
    container = SimpleNamespace(watchlist_service=SimpleNamespace())
    page = WatchlistPage(container=container)

    _assert_passive_table(page.stock_table)
    item = page._readonly_table_item("ASELS")
    assert item.flags() == Qt.ItemIsEnabled


def test_dashboard_summary_items_are_not_selectable():
    widget = DashboardPortfolioTable()

    widget.update_summary_row(Decimal("1000"), Decimal("50"))

    assert widget.table_summary.selectionMode() == QTableWidget.NoSelection
    for column in range(widget.table_summary.columnCount()):
        item = widget.table_summary.item(0, column)
        assert item.flags() == Qt.ItemIsEnabled


def test_dashboard_main_table_does_not_select_rows_but_keeps_double_click_surface():
    widget = DashboardPortfolioTable()
    model = PortfolioTableModel(
        positions=[Position(stock_id=1, total_quantity=10, total_cost=Decimal("100"))],
        price_map={1: Decimal("12")},
        ticker_map={1: "ASELS.IS"},
    )

    widget.set_model(model)
    index = model.index(0, 6)

    assert widget.table_view.selectionMode() == QTableView.NoSelection
    assert widget.table_view.focusPolicy() == Qt.NoFocus
    assert model.flags(index) == Qt.ItemIsEnabled
    assert not model.flags(index) & Qt.ItemIsSelectable
    assert model.data(index, Qt.ForegroundRole).name() == "#22c55e"

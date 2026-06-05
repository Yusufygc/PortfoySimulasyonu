import sys
from decimal import Decimal
from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QTableView, QTableWidget

from src.domain.models.watchlist import Watchlist
from src.domain.models.position import Position
from src.ui.pages.dashboard.dashboard_portfolio_table import DashboardPortfolioTable
from src.ui.pages.watchlist_page import WatchlistPage
from src.ui.portfolio_table_model import PortfolioTableModel
from src.ui.shared.locale_tr import L10N
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
            },
            {
                "ticker": "FROTO.IS",
                "quantity": 4,
                "avg_cost": Decimal("100"),
                "current_price": Decimal("90"),
                "current_value": Decimal("360"),
                "profit_loss": Decimal("-40"),
            }
        ]
    )

    _assert_passive_table(table)
    assert table.property("cssClass") == "modelPositionsTable"
    assert table.item(0, 0).text() == "ASELS"
    assert table.item(0, 0).data(Qt.UserRole) == {
        "stock_id": None,
        "ticker": "ASELS.IS",
        "name": None,
    }
    for row in range(table.rowCount()):
        for column in range(table.columnCount()):
            item = table.item(row, column)
            assert item.flags() == Qt.ItemIsEnabled
            assert item.textAlignment() == int(Qt.AlignCenter)
            assert item.toolTip() == "Hisse detaylarını görmek için çift tıkla"

    pl_item = table.item(0, 5)
    assert not pl_item.flags() & Qt.ItemIsSelectable
    assert pl_item.foreground().color().name() == "#00ff00"
    assert table.item(1, 5).foreground().color().name() == "#ff0000"

    emitted = []
    table.row_double_clicked.connect(emitted.append)
    table._on_cell_double_clicked(0, 0)
    assert emitted == [{"stock_id": None, "ticker": "ASELS.IS", "name": None}]
    assert table._update_hover_cursor(table.visualItemRect(table.item(0, 0)).center()) is True


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


def test_watchlist_actions_are_placed_in_headers_and_stock_name_is_clean():
    service = SimpleNamespace(
        get_watchlist_stocks=lambda watchlist_id: [
            {
                "item": SimpleNamespace(notes="deneme notu"),
                "stock": SimpleNamespace(id=1),
                "ticker": "ENKAI.IS",
                "name": "ENKAI.IS",
            }
        ]
    )
    page = WatchlistPage(container=SimpleNamespace(watchlist_service=service))

    assert page.list_widget.property("cssClass") == "watchlistList"
    assert page.btn_new.property("cssClass") == "watchlistNewButton"
    assert page._left_header_layout.indexOf(page.btn_new) >= 0
    assert page._detail_header_layout.indexOf(page.btn_add_stock) >= 0
    assert not page.btn_add_stock.isEnabled()

    item = page.list_widget.currentItem()
    if item is None:
        item = page.list_widget.item(0)
    if item is None:
        from PyQt5.QtWidgets import QListWidgetItem

        item = QListWidgetItem()
        page.list_widget.addItem(item)
    page._select_watchlist_item(item, Watchlist(id=1, name="deneme1", description=""))

    assert page.btn_add_stock.isEnabled()
    name_item = page.stock_table.item(0, 0)
    assert name_item.text() == "ENKAI"
    assert name_item.textAlignment() == int(Qt.AlignCenter)
    assert name_item.flags() == Qt.ItemIsEnabled
    assert name_item.data(Qt.UserRole)["ticker"] == "ENKAI.IS"


def test_watchlist_empty_state_replaces_table_for_empty_selected_list():
    service = SimpleNamespace(get_watchlist_stocks=lambda watchlist_id: [])
    page = WatchlistPage(container=SimpleNamespace(watchlist_service=service))

    from PyQt5.QtWidgets import QListWidgetItem

    item = QListWidgetItem()
    page.list_widget.addItem(item)
    page._select_watchlist_item(item, Watchlist(id=1, name="boş liste", description=""))

    assert page.list_widget.currentItem() is item
    assert page.content_stack.currentWidget() is page.empty_state
    assert page.btn_add_stock.isEnabled()
    assert page.btn_empty_add_stock.isEnabled()
    assert page.btn_empty_add_stock.property("cssClass") == "primaryButton"


def test_dashboard_summary_items_are_not_selectable():
    widget = DashboardPortfolioTable()

    widget.update_summary_row(Decimal("1000"), Decimal("50"))

    assert widget.table_summary.selectionMode() == QTableWidget.NoSelection
    assert widget.table_summary.columnCount() == 8
    assert widget.table_summary.item(0, 0).text() == L10N.TOPLAM_SATIRI
    assert widget.table_summary.item(0, 5).text() == "1,000.00"
    assert widget.table_summary.item(0, 7).text() == "+50.00"
    for column in range(widget.table_summary.columnCount()):
        item = widget.table_summary.item(0, column)
        assert item.flags() == Qt.ItemIsEnabled


def test_dashboard_main_table_does_not_select_rows_but_keeps_double_click_surface():
    widget = DashboardPortfolioTable()
    model = PortfolioTableModel(
        positions=[Position(stock_id=1, total_quantity=10, total_cost=Decimal("100"))],
        price_map={1: Decimal("12")},
        ticker_map={1: "ASELS.IS"},
        previous_close_map={1: Decimal("11")},
    )

    widget.set_model(model)
    index = model.index(0, 7)

    assert widget.table_view.selectionMode() == QTableView.NoSelection
    assert widget.table_view.focusPolicy() == Qt.NoFocus
    assert model.flags(index) == Qt.ItemIsEnabled
    assert not model.flags(index) & Qt.ItemIsSelectable
    assert model.data(index, Qt.ForegroundRole).name() == "#22c55e"

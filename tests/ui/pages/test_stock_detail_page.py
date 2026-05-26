import sys
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest

pytest.importorskip("PyQt5")
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QFormLayout, QHBoxLayout, QLabel, QSplitter, QTableWidget

from src.domain.models.trade import TradeSide
from src.ui.pages.stock_detail.stock_stats_panel import StockStatsPanel
from src.ui.pages.stock_detail.stock_chart_widget import StockChartWidget
from src.ui.pages.stock_detail.stock_detail_page import StockDetailPage
from src.ui.pages.stock_detail.trade_form_panel import TradeFormPanel
from src.ui.shared.card_factory import CardFactory
from src.ui.widgets.shared.controls.icon_label import IconLabel


app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class DummyPortfolioService:
    def __init__(self, trades=None):
        self._trades = trades or []

    def get_trades_for_stock(self, _stock_id):
        return list(self._trades)

    def get_current_portfolio(self):
        position = SimpleNamespace(
            total_quantity=12919,
            average_cost=Decimal("7.74"),
            total_cost=Decimal("99993.06"),
        )
        return SimpleNamespace(positions={1: position})


class DummyStockRepo:
    def get_stock_by_id(self, _stock_id):
        return SimpleNamespace(name="oba makarna")


def _stock_detail_page(trades=None):
    container = SimpleNamespace(
        portfolio_service=DummyPortfolioService(trades),
        stock_repo=DummyStockRepo(),
        trade_entry_service=SimpleNamespace(),
    )
    return StockDetailPage(container=container, price_lookup_func=None)


def test_trade_form_panel_is_compact_and_places_button_after_impact_card():
    panel = TradeFormPanel()
    layout = panel.layout()
    widgets = [layout.itemAt(index).widget() for index in range(layout.count())]
    form = layout.itemAt(1).layout()

    assert panel.minimumWidth() == 290
    assert panel.maximumWidth() == 290
    assert layout.contentsMargins().left() == 20
    assert layout.spacing() == 15
    assert isinstance(form, QFormLayout)
    assert form.spacing() == 15
    assert widgets.index(panel.btn_trade) == widgets.index(panel.impact_card) + 1


def test_card_factory_can_create_svg_icon_stat_card_without_emoji_text():
    card, value = CardFactory.create_stat_card(
        "TEST KART",
        "₺ 1.00",
        icon="💰",
        icon_name="wallet",
        icon_color="@COLOR_PRIMARY",
    )

    icon_labels = card.findChildren(IconLabel)

    assert icon_labels
    assert icon_labels[0]._icon_name == "wallet"
    assert all("💰" not in label.text() for label in card.findChildren(QLabel))


def test_stock_detail_page_does_not_use_splitter_for_trade_panel():
    page = _stock_detail_page()
    content_layout = page.main_layout.itemAt(page.main_layout.count() - 1).layout()

    assert isinstance(content_layout, QHBoxLayout)
    assert page.findChild(QSplitter) is None


def test_history_table_is_read_only_centered_and_non_selectable():
    trade = SimpleNamespace(
        trade_date=date(2025, 12, 4),
        side=TradeSide.BUY,
        quantity=12919,
        price=Decimal("7.74"),
        total_amount=Decimal("99993.06"),
    )
    page = _stock_detail_page([trade])
    page.current_stock_id = 1

    page._load_history()

    table = page.history_table
    assert table.selectionMode() == QTableWidget.NoSelection
    assert table.editTriggers() == QTableWidget.NoEditTriggers
    assert table.focusPolicy() == Qt.NoFocus

    for column in range(table.columnCount()):
        item = table.item(0, column)
        assert item.textAlignment() == Qt.AlignCenter
        assert item.flags() & Qt.ItemIsEnabled
        assert not item.flags() & Qt.ItemIsSelectable

    buy_item = table.item(0, 1)
    assert buy_item.text() == "ALIM"
    assert buy_item.foreground().color().name() == "#10b981"


def test_stock_stats_panel_uses_svg_icons_and_balanced_stretches():
    panel = StockStatsPanel()
    layout = panel.layout()
    icons = {
        icon._icon_name
        for card in (panel.card_total_val, panel.card_pl, panel.card_avg_cost, panel.card_total_qty)
        for icon in card.findChildren(IconLabel)
    }

    assert icons == {"wallet", "line-chart", "tag", "package"}
    assert [layout.stretch(index) for index in range(4)] == [8, 5, 4, 4]
    assert panel.card_pl.minimumWidth() >= 230


def test_stock_stats_panel_colors_profit_loss_and_updates_icon():
    panel = StockStatsPanel()

    panel.update_stats(DummyPortfolioService(), 1, Decimal("8.50"))

    assert panel.lbl_pl.property("cssState") == "positive"
    assert panel.card_pl.property("cssState") == "positive"
    assert panel._pl_icon_label._icon_name == "trending-up"

    loss_service = SimpleNamespace(
        get_current_portfolio=lambda: SimpleNamespace(
            positions={
                1: SimpleNamespace(
                    total_quantity=100,
                    average_cost=Decimal("10"),
                    total_cost=Decimal("1000"),
                )
            }
        )
    )

    panel.update_stats(loss_service, 1, Decimal("8"))

    assert panel.lbl_pl.property("cssState") == "negative"
    assert panel.card_pl.property("cssState") == "negative"
    assert panel._pl_icon_label._icon_name == "trending-down"

    panel.clear_stats()

    assert panel.lbl_pl.property("cssState") == "neutral"
    assert panel.card_pl.property("cssState") == "neutral"
    assert panel._pl_icon_label._icon_name == "line-chart"


def test_stock_chart_draws_empty_state_and_disables_date_si_prefix():
    chart = StockChartWidget()

    chart.draw_empty_chart("Veri bulunamadı")

    bottom_axis = chart.plot_widget.getPlotItem().getAxis("bottom")
    assert getattr(bottom_axis, "autoSIPrefix", None) is False
    assert chart.plot_widget.getPlotItem().titleLabel.text == "Veri bulunamadı"


def test_stock_chart_draws_price_series_with_pyqtgraph(monkeypatch):
    chart = StockChartWidget()
    data = pd.DataFrame(
        {"Close": [Decimal("7.50"), Decimal("7.80"), Decimal("7.96")]},
        index=pd.to_datetime(["2026-05-22", "2026-05-25", "2026-05-26"]),
    )
    monkeypatch.setattr(
        "src.ui.pages.stock_detail.stock_chart_widget.yf.download",
        lambda *args, **kwargs: data,
    )

    chart.draw_chart("OBAMS", 1, Decimal("7.96"), DummyPortfolioService())
    chart.draw_chart("OBAMS", 1, Decimal("7.96"), DummyPortfolioService())

    assert len(chart.plot_widget.listDataItems()) >= 1
    assert chart.plot_widget.getPlotItem().titleLabel.text == "OBAMS - Fiyat Geçmişi"
    assert chart._reference_legend is not None
    assert len(chart._reference_legend.items) == 2

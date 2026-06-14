import sys
from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6")
from src.qt_compat.qtcore import QDate, Qt
from src.qt_compat.qtwidgets import QApplication, QFormLayout, QHBoxLayout, QLabel, QSizePolicy, QSplitter, QTableWidget

from src.domain.models.trade import TradeSide
from src.domain.models.model_portfolio import ModelTradeSide
from src.ui.pages.stock_detail.stock_stats_panel import StockStatsPanel
from src.ui.pages.stock_detail.stock_chart_widget import StockChartWidget
from src.ui.pages.stock_detail.stock_detail_page import StockDetailPage
from src.ui.pages.stock_detail.trade_form_panel import TradeFormPanel
from src.ui.shared.card_factory import CardFactory, StatCardStyle
from src.ui.shared.locale_tr import L10N
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


class DummyModelPortfolioService:
    def __init__(self, trades=None):
        self._trades = trades or []
        self.add_calls = []

    def get_stock_trades(self, portfolio_id, stock_id):
        return list(self._trades)

    def get_positions_with_details(self, portfolio_id, price_map=None):
        price = (price_map or {}).get(1)
        return [
            {
                "stock_id": 1,
                "ticker": "SMRTG.IS",
                "name": "SMRTG.IS",
                "quantity": 25,
                "avg_cost": Decimal("10"),
                "total_cost": Decimal("250"),
                "current_price": price,
                "current_value": price * Decimal("25") if price else None,
                "profit_loss": (price * Decimal("25") - Decimal("250")) if price else None,
            }
        ]

    def add_trade_by_ticker(self, **kwargs):
        self.add_calls.append(kwargs)
        return SimpleNamespace(stock_id=1)


def _stock_detail_page(trades=None):
    container = SimpleNamespace(
        portfolio_service=DummyPortfolioService(trades),
        stock_repo=DummyStockRepo(),
        trade_entry_service=SimpleNamespace(),
        model_portfolio_service=DummyModelPortfolioService(),
        price_repo=SimpleNamespace(get_price_series=lambda *args, **kwargs: []),
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


def test_trade_form_panel_clamps_remaining_cash_preview_to_zero():
    panel = TradeFormPanel()
    panel.spin_qty.setValue(2)
    panel.spin_price.setValue(10)

    panel.update_impact_preview(DummyPortfolioService(), 1, cash_balance=Decimal("0"))

    values = [
        panel.impact_grid.itemAt(row, QFormLayout.FieldRole).widget().text()
        for row in range(panel.impact_grid.rowCount())
    ]
    assert "₺ 0.00" in values
    assert "Yetersiz Nakit" in values
    assert all("-" not in value for value in values)


def test_card_factory_can_create_svg_icon_stat_card_without_emoji_text():
    card, value = CardFactory.create_stat_card(
        "TEST KART",
        "₺ 1.00",
        StatCardStyle(icon="💰", icon_name="wallet", icon_color="@COLOR_PRIMARY"),
    )

    icon_labels = card.findChildren(IconLabel)

    assert icon_labels
    assert icon_labels[0]._icon_name == "wallet"
    assert all("💰" not in label.text() for label in card.findChildren(QLabel))


def test_stock_detail_page_does_not_use_splitter_for_trade_panel():
    page = _stock_detail_page()
    content_scroll = page.main_layout.itemAt(page.main_layout.count() - 1).widget()
    content_layout = page.content_wrapper.layout()

    assert content_scroll is page.content_scroll_area
    assert isinstance(content_layout, QHBoxLayout)
    assert page.findChild(QSplitter) is None


def test_stock_detail_page_prevents_trade_panel_overlap_when_narrow(qapp):
    page = _stock_detail_page()
    content_layout = page.content_wrapper.layout()
    expected_min_width = (
        page._LEFT_CONTENT_MIN_WIDTH
        + content_layout.spacing()
        + page.trade_form.minimumWidth()
    )

    assert page.content_scroll_area.horizontalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    assert page.scroll_area.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    assert page.trade_form.minimumWidth() == 290
    assert page.trade_form.maximumWidth() == 290
    assert page.content_wrapper.minimumWidth() >= expected_min_width

    page.resize(800, 700)
    page.show()
    qapp.processEvents()

    assert not page.scroll_area.geometry().intersects(page.trade_form.geometry())
    assert page.scroll_area.geometry().right() < page.trade_form.geometry().left()
    assert page.content_scroll_area.horizontalScrollBar().maximum() > 0


def test_trade_form_panel_allows_future_date_selection_but_warns_on_submit(qapp, monkeypatch):
    panel = TradeFormPanel()
    warnings = []
    submitted = []
    future = QDate.currentDate().addDays(1)
    monkeypatch.setattr(
        "src.ui.pages.stock_detail.trade_form_panel.QMessageBox.warning",
        lambda *args, **kwargs: warnings.append(args[2]),
    )
    panel.trade_submitted.connect(lambda *args: submitted.append(args))

    panel.date_edit.setDate(future)
    panel._submit_trade()

    assert panel.date_edit.date() == future
    assert warnings == [L10N.GELECEK_TARIHLI_ISLEM_GIRILEMEZ]
    assert submitted == []


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


def _history_trade(index: int):
    return SimpleNamespace(
        id=index,
        trade_date=date(2026, 6, 1),
        trade_time=time(10, 0, index % 60),
        side=TradeSide.BUY if index % 2 == 0 else TradeSide.SELL,
        quantity=index + 1,
        price=Decimal("10"),
        total_amount=Decimal("10"),
    )


def _expected_history_table_height(page: StockDetailPage, visible_rows: int) -> int:
    table = page.history_table
    default_row_height = table.verticalHeader().defaultSectionSize()
    row_height = sum(table.rowHeight(row) or default_row_height for row in range(visible_rows))
    header_height = table.horizontalHeader().height() or table.horizontalHeader().sizeHint().height()
    return header_height + row_height + (table.frameWidth() * 2) + 2


@pytest.mark.parametrize("trade_count", [4, 10])
def test_history_table_grows_without_internal_scroll_until_ten_rows(trade_count):
    page = _stock_detail_page([_history_trade(index) for index in range(trade_count)])
    page.current_stock_id = 1

    page._load_history()

    assert page.history_table.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    assert page.history_table.minimumHeight() == _expected_history_table_height(page, trade_count)
    assert page.history_table.maximumHeight() == page.history_table.minimumHeight()


def test_history_table_uses_internal_scroll_after_ten_rows():
    page = _stock_detail_page([_history_trade(index) for index in range(11)])
    page.current_stock_id = 1

    page._load_history()

    assert page.history_table.verticalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    assert page.history_table.minimumHeight() == _expected_history_table_height(page, 10)
    assert page.history_table.maximumHeight() == page.history_table.minimumHeight()


def test_corporate_actions_table_scroll_behavior_is_unchanged():
    page = _stock_detail_page()

    assert page.corp_actions_table.minimumHeight() == 150
    assert page.corp_actions_table.sizePolicy().verticalPolicy() == QSizePolicy.Expanding


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


def test_stock_chart_draws_price_series_with_pyqtgraph(drain_qt_events):
    chart = StockChartWidget()
    series = {
        date(2026, 5, 22): Decimal("7.50"),
        date(2026, 5, 25): Decimal("7.80"),
        date(2026, 5, 26): Decimal("7.96"),
    }
    chart.set_price_series_provider(lambda ticker, start, end: series)

    chart.draw_chart("OBAMS", 1, Decimal("7.96"), DummyPortfolioService())
    chart.draw_chart("OBAMS", 1, Decimal("7.96"), DummyPortfolioService())
    drain_qt_events()

    assert len(chart.plot_widget.listDataItems()) >= 1
    assert chart.plot_widget.getPlotItem().titleLabel.text == "OBAMS — Fiyat Geçmişi"
    assert chart._reference_legend is not None
    assert len(chart._reference_legend.items) == 2


def test_stock_detail_model_context_uses_model_history_and_stats():
    trade = SimpleNamespace(
        trade_date=date(2026, 5, 1),
        side=ModelTradeSide.BUY,
        quantity=25,
        price=Decimal("10"),
        total_amount=Decimal("250"),
    )
    service = DummyModelPortfolioService([trade])
    page = _stock_detail_page()
    page.model_portfolio_service = service
    page.current_ticker = "SMRTG.IS"
    page.current_stock_id = 1
    page.current_price = Decimal("12")
    page._detail_context = {"source": "model_portfolio", "portfolio_id": 3, "price_map": {1: Decimal("12")}}

    page.stats_panel.update_model_stats = lambda *args, **kwargs: setattr(page, "_model_stats_called", args)
    page.chart_widget.draw_chart = lambda *args, **kwargs: None
    page.refresh_data()

    assert page._model_stats_called[1:4] == (3, 1, Decimal("12"))
    assert page.history_table.item(0, 1).text() == "ALIM"
    assert page.history_table.item(0, 1).foreground().color().name() == "#10b981"


def test_stock_detail_model_submit_writes_model_trade(monkeypatch):
    service = DummyModelPortfolioService()
    page = _stock_detail_page()
    page.model_portfolio_service = service
    page.current_ticker = "SMRTG.IS"
    page.current_stock_id = 1
    page._detail_context = {"source": "model_portfolio", "portfolio_id": 3, "price_map": {}}
    page.refresh_data = lambda: None
    page._trigger_impact_update = lambda: None
    monkeypatch.setattr("src.ui.pages.stock_detail.stock_detail_page.QMessageBox.information", lambda *args, **kwargs: None)

    expected_time = page.trade_form.time_edit.time().toPyTime()
    page._on_submit_trade(True, 2, 11.75, SimpleNamespace(toPyDate=lambda: date(2026, 5, 26)))

    assert service.add_calls == [
        {
            "portfolio_id": 3,
            "ticker": "SMRTG.IS",
            "side": "BUY",
            "quantity": 2,
            "price": Decimal("11.75"),
            "trade_date": date(2026, 5, 26),
            "trade_time": expected_time,
        }
    ]


def test_stock_detail_real_submit_warns_when_trade_validation_fails(monkeypatch):
    page = _stock_detail_page()
    page.current_ticker = "ASELS.IS"
    page.current_stock_id = 1
    page.trade_entry_service = SimpleNamespace(
        submit_trade=lambda **kwargs: (_ for _ in ()).throw(ValueError("Yetersiz pozisyon"))
    )
    warnings = []
    monkeypatch.setattr(
        "src.ui.pages.stock_detail.stock_detail_page.QMessageBox.warning",
        lambda *args, **kwargs: warnings.append(args[2]),
    )

    page._on_submit_trade(False, 999, 10.0, SimpleNamespace(toPyDate=lambda: date(2026, 5, 26)))

    assert warnings == ["Yetersiz pozisyon"]


def test_stock_detail_submit_blocks_closed_market_session(monkeypatch):
    page = _stock_detail_page()
    page.current_ticker = "ASELS.IS"
    page.current_stock_id = 1
    page.market_session_service = SimpleNamespace(
        status_for=lambda trade_date, trade_time=None: SimpleNamespace(
            is_open=False,
            message="Kapali seans",
        )
    )
    calls = []
    page.trade_entry_service = SimpleNamespace(submit_trade=lambda **kwargs: calls.append(kwargs))
    warnings = []
    monkeypatch.setattr(
        "src.ui.pages.stock_detail.stock_detail_page.QMessageBox.warning",
        lambda *args, **kwargs: warnings.append(args[2]),
    )

    page._on_submit_trade(
        True,
        2,
        11.75,
        SimpleNamespace(toPyDate=lambda: date(2026, 6, 6)),
        SimpleNamespace(toPyTime=lambda: time(11, 0)),
    )

    assert calls == []
    assert warnings
    assert "BIST" in warnings[0]


def test_stock_chart_uses_db_series_before_provider(drain_qt_events):
    chart = StockChartWidget()
    price_repo = SimpleNamespace(
        get_price_series=lambda *args: [
            SimpleNamespace(price_date=date(2026, 5, 24), close_price=Decimal("10")),
            SimpleNamespace(price_date=date(2026, 5, 25), close_price=Decimal("11")),
        ]
    )
    chart.set_price_series_provider(
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("provider should not be called")),
    )

    chart.draw_chart("SMRTG.IS", 1, Decimal("11"), None, price_repo=price_repo, average_cost=Decimal("9"))
    drain_qt_events()

    assert len(chart.plot_widget.listDataItems()) >= 1


def test_stock_chart_falls_back_to_provider_when_db_empty(drain_qt_events):
    chart = StockChartWidget()
    calls = []

    def provider(ticker, start, end):
        calls.append(ticker)
        return {date(2026, 5, 25): Decimal("11")}

    chart.set_price_series_provider(provider)
    chart.draw_chart("SMRTG", 1, Decimal("11"), None, price_repo=None)
    drain_qt_events()

    assert calls == ["SMRTG.IS"]  # UI .IS normalizasyonunu korur
    assert len(chart.plot_widget.listDataItems()) >= 1


def test_stock_chart_widget_does_not_import_yfinance():
    import src.ui.pages.stock_detail.stock_chart_widget as chart_module

    assert not hasattr(chart_module, "yf")


def test_stock_chart_date_axis_uses_turkish_months():
    from datetime import datetime
    from src.ui.pages.stock_detail.stock_chart_widget import DateAxisItem

    axis = DateAxisItem(orientation="bottom")
    ts = datetime(2026, 1, 15).timestamp()

    labels = axis.tickStrings([ts], 1, 1)

    assert labels == ["15 Oca"]


def test_stock_chart_currency_axis_formats_with_tl_symbol():
    from src.ui.pages.stock_detail.stock_chart_widget import CurrencyAxisItem

    axis = CurrencyAxisItem(orientation="left")

    labels = axis.tickStrings([1234.56], 1, 1)

    assert labels == ["₺ 1.234,56"]


def test_stock_chart_crosshair_snaps_to_nearest_point():
    from src.ui.pages.stock_detail.stock_chart_widget import StockChartWidget

    chart = StockChartWidget()
    chart._chart_points = [(100.0, 10.0), (200.0, 20.0), (300.0, 30.0)]

    # 240 → 200 (40) ile 300 (60) arasından 200'e daha yakın
    snap = chart._nearest_point(240.0)

    assert snap == (200.0, 20.0)


def test_stock_chart_reference_legend_offset_avoids_title_overlap():
    """Reference legend başlık satırının altında konumlanır (Y >= 40)."""
    from decimal import Decimal
    from datetime import date
    from src.ui.pages.stock_detail.stock_chart_widget import StockChartWidget

    chart = StockChartWidget()
    series = {date(2026, 5, 22): Decimal("7.50"), date(2026, 5, 25): Decimal("7.80")}
    chart.set_price_series_provider(lambda *_: series)
    chart.draw_chart("OBAMS", 1, Decimal("7.80"), DummyPortfolioService())

    # Worker async; offset doğrudan kaynaktan teyit edilebilir
    chart._add_reference_legend_item("test", None)
    legend = chart._reference_legend
    # pg.LegendItem offset (14, 44) → __init__'te _offset attribute olarak saklanır
    offset = getattr(legend, "_offset", None) or getattr(legend, "offset", None)
    # offset tuple veya callable olabilir; tuple kabulü
    if callable(offset):
        offset = offset()
    assert offset[1] >= 40, f"Legend Y-offset başlığın altında olmalı, oldu: {offset}"


def test_stock_detail_page_async_price_lookup_success(drain_qt_events):
    lookup_calls = []

    class DummyResult:
        def __init__(self, price):
            self.price = Decimal(str(price))

    def lookup_price(ticker):
        lookup_calls.append(ticker)
        return DummyResult(55.50)

    container = SimpleNamespace(
        portfolio_service=DummyPortfolioService([]),
        stock_repo=DummyStockRepo(),
        trade_entry_service=SimpleNamespace(),
        model_portfolio_service=DummyModelPortfolioService(),
        price_repo=SimpleNamespace(get_price_series=lambda *args, **kwargs: []),
    )
    page = StockDetailPage(container=container, price_lookup_func=lookup_price)
    page.current_ticker = "ASELS.IS"
    page.current_stock_id = 1

    page.chart_widget.draw_chart = lambda *args, **kwargs: None

    # Trigger set_stock
    page.set_stock("ASELS.IS", stock_id=1)

    # The price label should initially show "Fiyat Yükleniyor..."
    assert page.lbl_price.text() == "Fiyat Yükleniyor..."

    # Process events to let worker run
    drain_qt_events()

    # Check that lookup_price was called and UI is updated
    assert "ASELS.IS" in lookup_calls
    assert page.current_price == Decimal("55.50")
    assert page.lbl_price.text() == "TL 55.50"


def test_stock_detail_page_async_price_lookup_race_condition(drain_qt_events):
    import time as py_time

    class DummyResult:
        def __init__(self, price):
            self.price = Decimal(str(price))

    def lookup_price(ticker):
        if ticker == "SLOW.IS":
            py_time.sleep(0.1)  # Simulate slow lookup
            return DummyResult(100.0)
        return DummyResult(200.0)

    container = SimpleNamespace(
        portfolio_service=DummyPortfolioService([]),
        stock_repo=DummyStockRepo(),
        trade_entry_service=SimpleNamespace(),
        model_portfolio_service=DummyModelPortfolioService(),
        price_repo=SimpleNamespace(get_price_series=lambda *args, **kwargs: []),
    )
    page = StockDetailPage(container=container, price_lookup_func=lookup_price)
    page.chart_widget.draw_chart = lambda *args, **kwargs: None

    # Set slow stock first
    page.set_stock("SLOW.IS", stock_id=1)

    # Immediately switch to FAST.IS
    page.set_stock("FAST.IS", stock_id=2)

    drain_qt_events()

    # The final stock price should be 200.0, and slow stock's 100.0 should be ignored
    assert page.current_ticker == "FAST.IS"
    assert page.current_price == Decimal("200.0")
    assert page.lbl_price.text() == "TL 200.00"

import sys
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")
from PyQt5.QtWidgets import QApplication

from src.domain.models.model_portfolio import ModelPortfolio
from src.ui.pages.model_portfolio.model_portfolio_page import ModelPortfolioPage
from src.ui.widgets.model_portfolio.panels.portfolio_list_panel import PortfolioListPanel


app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class DummyModelPortfolioService:
    def get_positions_with_details(self, portfolio_id):
        return [{"stock_id": 2, "ticker": "BBB.IS"}]


class DummyPriceRepo:
    def __init__(self):
        self.saved_prices = []

    def upsert_daily_prices_bulk(self, prices):
        self.saved_prices.extend(prices)


class DummyEventSignal:
    def __init__(self):
        self.emitted = []

    def emit(self, payload):
        self.emitted.append(payload)


class EmptyModelPortfolioService:
    def get_portfolio_summary(self, portfolio_id, price_map):
        return {
            "initial_cash": Decimal("1000000"),
            "remaining_cash": Decimal("1000000"),
            "total_value": Decimal("1000000"),
            "profit_loss": Decimal("0"),
        }

    def get_positions_with_details(self, portfolio_id, price_map=None):
        return []

    def get_first_trade_date(self, portfolio_id):
        return date(2026, 1, 2)


class DummyModelPortfolioExcelExportService:
    def __init__(self):
        self.calls = []

    def export_model_portfolio_history(self, portfolio_id, start_date, end_date, file_path, mode):
        self.calls.append((portfolio_id, start_date, end_date, file_path, mode))


def test_model_portfolio_list_panel_header_new_button_and_selection_class():
    panel = PortfolioListPanel()

    assert panel._btn_new.property("cssClass") == "modelPortfolioNewButton"
    assert panel._header_layout.indexOf(panel._btn_new) >= 0
    assert panel._list.property("cssClass") == "modelPortfolioList"


def test_model_portfolio_page_moves_trade_buttons_to_positions_header_and_shows_empty_state():
    export_service = DummyModelPortfolioExcelExportService()
    page = ModelPortfolioPage(
        container=SimpleNamespace(
            model_portfolio_service=EmptyModelPortfolioService(),
            price_repo=SimpleNamespace(),
            model_portfolio_excel_export_service=export_service,
        )
    )

    assert page._positions_header_layout.indexOf(page.btn_buy) >= 0
    assert page._positions_header_layout.indexOf(page.btn_sell) >= 0
    assert not page.btn_report.isEnabled()
    assert [action.text() for action in page.btn_report.menu().actions()] == ["Bugün", "Tarih Aralığı"]
    assert not page.btn_buy.isEnabled()
    assert not page.btn_sell.isEnabled()
    assert not page.btn_empty_buy.isEnabled()

    page._set_current_portfolio(ModelPortfolio(id=7, name="boş portföy"))

    assert page.positions_stack.currentWidget() is page.empty_positions_state
    assert page.btn_buy.isEnabled()
    assert page.btn_sell.isEnabled()
    assert page.btn_report.isEnabled()
    assert page.btn_empty_buy.isEnabled()
    assert page.btn_empty_buy.property("cssClass") == "successButton"


def test_model_portfolio_position_double_click_opens_stock_detail():
    page = ModelPortfolioPage.__new__(ModelPortfolioPage)
    page.current_portfolio_id = 5
    page.current_price_map = {12: Decimal("97.50")}
    calls = []
    page.window = lambda: SimpleNamespace(
        show_stock_detail=lambda ticker, stock_id, context=None: calls.append((ticker, stock_id, context))
    )

    ModelPortfolioPage._on_position_double_clicked(page, {"ticker": "FROTO.IS", "stock_id": 12})

    assert calls == [
        (
            "FROTO.IS",
            12,
            {"source": "model_portfolio", "portfolio_id": 5, "price_map": {12: Decimal("97.50")}},
        )
    ]


def test_model_portfolio_export_today_uses_history_report(tmp_path, monkeypatch):
    export_service = DummyModelPortfolioExcelExportService()
    page = ModelPortfolioPage.__new__(ModelPortfolioPage)
    page.current_portfolio_id = 8
    page.lbl_portfolio_name = SimpleNamespace(text=lambda: "deneme portföy")
    page.list_panel = SimpleNamespace(current_portfolio=lambda: ModelPortfolio(id=8, name="deneme portföy"))
    page.model_portfolio_excel_export_service = export_service
    page.model_portfolio_service = SimpleNamespace(get_first_trade_date=lambda portfolio_id: date(2026, 1, 2))

    file_path = str(tmp_path / "model.xlsx")
    monkeypatch.setattr(
        "src.ui.pages.model_portfolio.utils.portfolio_exporter.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: (file_path, "Excel Dosyaları (*.xlsx)"),
    )
    monkeypatch.setattr(
        "src.ui.pages.model_portfolio.utils.portfolio_exporter.QMessageBox.information",
        lambda *args, **kwargs: None,
    )

    monkeypatch.setattr("src.ui.pages.model_portfolio.utils.portfolio_exporter.date", SimpleNamespace(today=lambda: date(2026, 5, 26)))

    ModelPortfolioPage._on_export_today(page)

    assert export_service.calls[0][0:4] == (8, date(2026, 1, 2), date(2026, 5, 26), file_path)


def test_model_portfolio_refresh_persists_prices_to_daily_prices():
    price_repo = DummyPriceRepo()
    event_signal = DummyEventSignal()
    page = ModelPortfolioPage.__new__(ModelPortfolioPage)
    page.current_portfolio_id = 4
    page.model_portfolio_service = DummyModelPortfolioService()
    page.price_repo = price_repo
    page.current_price_map = {}
    page.container = SimpleNamespace(event_bus=SimpleNamespace(prices_updated=event_signal))
    page.price_lookup_func = lambda ticker: SimpleNamespace(
        price=Decimal("22.50"),
        as_of=datetime(2026, 4, 28, 12, 0),
        source="intraday",
    )
    page._update_view = lambda: None
    page.record_last_update_time = lambda: None
    page.show_last_update_toast_once = lambda **kwargs: None

    ModelPortfolioPage._on_refresh_prices(page)

    assert page.current_price_map == {2: Decimal("22.50")}
    assert len(price_repo.saved_prices) == 1
    assert price_repo.saved_prices[0].stock_id == 2
    assert price_repo.saved_prices[0].close_price == Decimal("22.50")
    assert event_signal.emitted == [{2: Decimal("22.50")}]

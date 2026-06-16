import sys
from datetime import date, datetime, time
from decimal import Decimal
from types import SimpleNamespace

import pytest
from decimal import Decimal
from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6")
from src.qt_compat.qtwidgets import QApplication, QDialog, QPushButton

from src.application.services.market.price_data_health_service import PriceDataHealthReport, StockPriceHealthRow
from src.domain.models.model_portfolio import ModelPortfolio
from src.ui.pages.model_portfolio.model_portfolio_page import ModelPortfolioPage
from src.ui.pages.model_portfolio.model_portfolio_presenter import ModelPortfolioPresenter
from src.ui.pages.model_portfolio.utils.model_portfolio_actions import ModelPortfolioActions
from src.ui.shared.locale_tr import L10N
from src.ui.widgets.shared import ActionListItem
from src.ui.widgets.shared.cards.info_card import InfoCard
from src.ui.widgets.model_portfolio.panels.portfolio_list_panel import PortfolioListPanel


app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class DummyModelPortfolioService:
    def get_positions_with_details(self, portfolio_id, price_map=None):
        return [{"stock_id": 2, "ticker": "BBB.IS"}]

    def get_positions(self, portfolio_id):
        return {2: SimpleNamespace(quantity=Decimal("1"))}

    def get_portfolio_summary(self, portfolio_id, price_map):
        return {
            "initial_cash": Decimal("1000000"),
            "net_capital": Decimal("1000000"),
            "remaining_cash": Decimal("1000000"),
            "total_value": Decimal("1000000"),
            "profit_loss": Decimal("0"),
        }


class DummyPriceRepo:
    def __init__(self):
        self.saved_prices = []

    def upsert_daily_prices_bulk(self, prices):
        self.saved_prices.extend(prices)


class DummyLatestPriceRepo:
    def __init__(self, price_map=None):
        self.price_map = dict(price_map or {})
        self.saved_prices = []

    def get_latest_price_map(self, stock_ids):
        return {
            stock_id: self.price_map[stock_id]
            for stock_id in stock_ids
            if stock_id in self.price_map
        }

    def upsert_latest_prices(self, prices):
        self.saved_prices.extend(list(prices))


class DummyEventSignal:
    def __init__(self):
        self.emitted = []

    def emit(self, payload):
        self.emitted.append(payload)


class EmptyModelPortfolioService:
    def __init__(self):
        self.portfolios = []

    def get_all_portfolios(self):
        return list(self.portfolios)

    def get_active_position_count(self, portfolio_id):
        return 0

    def get_portfolio_summary(self, portfolio_id, price_map):
        return {
            "initial_cash": Decimal("1000000"),
            "net_capital": Decimal("1000000"),
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


def test_action_list_item_elides_secondary_text_and_keeps_menu_fixed():
    row = ActionListItem(
        "portfoy-4",
        secondary_text="(8 hisse)",
        draggable=True,
    )

    assert row.label is not None
    assert row.secondary_label is not None
    assert row.menu_button.width() == 28
    assert row.menu_button.minimumWidth() == 28
    assert row.menu_button.maximumWidth() == 28
    assert row._layout.spacing() == 6

    row.show()
    app.processEvents()

    label_metrics = row.label.fontMetrics()
    metrics = row.secondary_label.fontMetrics()
    primary_full_width = label_metrics.horizontalAdvance("portfoy-4")
    secondary_full_width = metrics.horizontalAdvance("(8 hisse)")
    secondary_short_width = metrics.horizontalAdvance("(8 h.)")
    assert row.label.minimumSizeHint().width() <= 18
    assert row.secondary_label.minimumSizeHint().width() == 34

    margins = row._layout.contentsMargins()
    fixed_row_width = (
        margins.left()
        + margins.right()
        + row.drag_handle.width()
        + row.menu_button.width()
        + row._layout.spacing() * (row._layout.count() - 1)
    )

    row.resize(fixed_row_width + primary_full_width + secondary_full_width + 8, 44)
    app.processEvents()
    row._layout.activate()

    assert row.secondary_label.elided_text_for_width(row.secondary_label.width()) == "(8 hisse)"

    row.resize(fixed_row_width + primary_full_width + secondary_short_width + 2, 44)
    app.processEvents()
    row._layout.activate()

    assert row.label.elided_text_for_width(row.label.width()) == "portfoy-4"
    assert row.secondary_label.elided_text_for_width(row.secondary_label.width()) == "(8 h.)"

    row.resize(96, 44)
    app.processEvents()
    row._layout.activate()

    assert row.menu_button.width() == 28
    assert row.secondary_label.elided_text_for_width(row.secondary_label.width()) == "(8 h.)"
    assert row.secondary_label.geometry().right() < row.menu_button.geometry().left()


def test_model_portfolio_page_moves_trade_buttons_to_toolbar_and_shows_empty_state():
    export_service = DummyModelPortfolioExcelExportService()
    page = ModelPortfolioPage(
        container=SimpleNamespace(
            model_portfolio_service=EmptyModelPortfolioService(),
            price_repo=SimpleNamespace(),
            model_portfolio_excel_export_service=export_service,
        )
    )

    assert page._buttons_layout.indexOf(page.btn_new_trade) >= 0
    assert page._buttons_layout.indexOf(page.btn_refresh) >= 0
    assert page.btn_capital.property("cssClass") == "capitalButton"
    assert page.btn_report.property("cssClass") == "reportButton"
    assert page._buttons_layout.indexOf(page.btn_capital) < page._buttons_layout.indexOf(page.btn_report)
    assert not page.btn_report.isEnabled()
    assert not page.btn_capital.isEnabled()
    assert [action.text() for action in page.btn_report.menu().actions()] == ["Bugün", "Tarih Aralığı"]
    assert not page.btn_new_trade.isEnabled()
    assert not page.btn_empty_trade.isEnabled()

    page._set_current_portfolio(ModelPortfolio(id=7, name="boş portföy"))

    assert page.positions_stack.currentWidget() is page.empty_positions_state
    assert page.btn_new_trade.isEnabled()
    assert page.btn_report.isEnabled()
    assert page.btn_capital.isEnabled()
    assert page.btn_empty_trade.isEnabled()
    assert page.btn_empty_trade.property("cssClass") == "primaryButton"


def test_model_portfolio_page_selects_first_portfolio_when_saved_selection_is_missing():
    service = EmptyModelPortfolioService()
    service.portfolios = [
        ModelPortfolio(id=7, name="ilk portföy"),
        ModelPortfolio(id=8, name="ikinci portföy"),
    ]
    page = ModelPortfolioPage(
        container=SimpleNamespace(
            model_portfolio_service=service,
            price_repo=SimpleNamespace(),
            model_portfolio_excel_export_service=DummyModelPortfolioExcelExportService(),
        )
    )
    page.current_portfolio_id = 999

    page._load_portfolios()

    assert page.current_portfolio_id == 7
    assert page.lbl_portfolio_name.text() == "ilk portföy"
    assert page.btn_new_trade.isEnabled()
    assert page.btn_capital.isEnabled()


def test_model_portfolio_page_clears_right_panel_when_no_portfolios():
    page = ModelPortfolioPage(
        container=SimpleNamespace(
            model_portfolio_service=EmptyModelPortfolioService(),
            price_repo=SimpleNamespace(),
            model_portfolio_excel_export_service=DummyModelPortfolioExcelExportService(),
        )
    )
    page.current_portfolio_id = 7

    page._load_portfolios()

    assert page.current_portfolio_id is None
    assert not page.btn_new_trade.isEnabled()
    assert not page.btn_refresh.isEnabled()
    assert not page.btn_report.isEnabled()
    assert not page.btn_capital.isEnabled()


def test_model_portfolio_update_view_passes_previous_close_map(monkeypatch):
    monkeypatch.setattr(
        "src.ui.pages.model_portfolio.model_portfolio_presenter.date",
        SimpleNamespace(today=lambda: date(2026, 6, 5)),
    )
    monkeypatch.setattr(
        "src.ui.shared.price_utils.date",
        SimpleNamespace(today=lambda: date(2026, 6, 5)),
    )
    calls = []

    class FakeService:
        def get_portfolio_summary(self, portfolio_id, price_map):
            return {
                "initial_cash": Decimal("1000"),
                "net_capital": Decimal("1000"),
                "remaining_cash": Decimal("100"),
                "total_value": Decimal("1200"),
                "profit_loss": Decimal("200"),
            }

        def get_positions_with_details(self, portfolio_id, price_map):
            return [
                {
                    "stock_id": 2,
                    "ticker": "ASELS.IS",
                    "quantity": 10,
                    "avg_cost": Decimal("20"),
                    "total_cost": Decimal("200"),
                    "current_price": Decimal("25"),
                }
            ]

    class FakePriceRepo:
        def get_last_price_before(self, stock_id, point_date):
            calls.append(("previous_close", stock_id, point_date))
            return SimpleNamespace(close_price=Decimal("24"))

    class FakePositionsTable:
        def populate(self, positions, previous_close_map=None):
            calls.append(("populate", positions, previous_close_map))

    card = SimpleNamespace(set_value=lambda *_args: None, set_value_state=lambda *_args: None)
    page = ModelPortfolioPage.__new__(ModelPortfolioPage)
    page.current_portfolio_id = 7
    page.current_price_map = {2: Decimal("25")}
    page.model_portfolio_service = FakeService()
    page.price_repo = FakePriceRepo()
    page.card_initial = card
    page.card_cash = card
    page.card_value = card
    page.card_pl = card
    page.positions_table = FakePositionsTable()
    page.positions_stack = SimpleNamespace(setCurrentWidget=lambda widget: calls.append(("stack", widget)))
    page.empty_positions_state = object()

    page._presenter = ModelPortfolioPresenter(page)
    page._presenter.update_view()

    assert ("previous_close", 2, date(2026, 6, 5)) in calls
    populate_call = next(call for call in calls if call[0] == "populate")
    assert populate_call[2] == {2: Decimal("24")}


def test_model_portfolio_load_current_price_map_prefers_latest_then_daily(monkeypatch):
    monkeypatch.setattr(
        "src.ui.pages.model_portfolio.model_portfolio_presenter.date",
        SimpleNamespace(today=lambda: date(2026, 6, 5)),
    )
    page = ModelPortfolioPage.__new__(ModelPortfolioPage)
    page.model_portfolio_service = SimpleNamespace(get_positions=lambda portfolio_id: {2: object(), 3: object()})
    page.latest_price_repo = DummyLatestPriceRepo({2: Decimal("22.50")})
    page.price_repo = SimpleNamespace(
        get_last_price_before=lambda stock_id, point_date: (
            SimpleNamespace(close_price=Decimal("31.40"))
            if stock_id == 3 and point_date == date(2026, 6, 5)
            else None
        )
    )

    page._presenter = ModelPortfolioPresenter(page)
    price_map = page._presenter.load_current_price_map(4)

    assert price_map == {2: Decimal("22.50"), 3: Decimal("31.40")}


def test_info_card_keeps_large_value_class_for_long_text_and_state_changes():
    card = InfoCard("K/Z", "TL 0")

    card.set_value("TL +42,082.82")
    card.set_value_state("positive")

    value_label = card.get_value_label()
    assert value_label.property("cssClass") == "infoCardValue"
    assert value_label.property("cssState") == "positive"


def test_model_portfolio_update_view_sets_profit_loss_card_state_for_positive_and_zero():
    class FakeService:
        def __init__(self, profit_loss):
            self._profit_loss = profit_loss

        def get_portfolio_summary(self, portfolio_id, price_map):
            return {
                "initial_cash": Decimal("1000"),
                "net_capital": Decimal("1000"),
                "remaining_cash": Decimal("100"),
                "total_value": Decimal("1200"),
                "profit_loss": self._profit_loss,
            }

        def get_positions_with_details(self, portfolio_id, price_map):
            return []

    class RecordingCard:
        def __init__(self):
            self.values = []
            self.states = []

        def set_value(self, value):
            self.values.append(value)

        def set_value_state(self, state):
            self.states.append(state)

    def build_page(profit_loss):
        neutral_card = SimpleNamespace(set_value=lambda *_args: None, set_value_state=lambda *_args: None)
        pl_card = RecordingCard()
        page = ModelPortfolioPage.__new__(ModelPortfolioPage)
        page.current_portfolio_id = 7
        page.current_price_map = {}
        page.model_portfolio_service = FakeService(profit_loss)
        page.price_repo = SimpleNamespace()
        page.card_initial = neutral_card
        page.card_cash = neutral_card
        page.card_value = neutral_card
        page.card_pl = pl_card
        page.positions_table = SimpleNamespace(populate=lambda positions, previous_close_map=None: None)
        page.positions_stack = SimpleNamespace(setCurrentWidget=lambda widget: None)
        page.empty_positions_state = object()
        return page, pl_card

    positive_page, positive_card = build_page(Decimal("200"))
    zero_page, zero_card = build_page(Decimal("0"))

    positive_page._presenter = ModelPortfolioPresenter(positive_page)
    zero_page._presenter = ModelPortfolioPresenter(zero_page)
    
    positive_page._presenter.update_view()
    zero_page._presenter.update_view()

    assert positive_card.values[-1] == "TL +200.00"
    assert positive_card.states[-1] == "positive"
    assert zero_card.values[-1] == L10N.TL_000
    assert zero_card.states[-1] == "neutral"


def test_model_portfolio_capital_action_passes_dialog_result_to_service(monkeypatch):
    calls = []

    class FakeDialog:
        def __init__(self, current_cash, net_capital, parent=None):
            calls.append(("dialog", current_cash, net_capital))

        def exec(self):
            return QDialog.Accepted

        def get_result(self):
            return {
                "movement_type": "DEPOSIT",
                "amount": Decimal("500"),
                "movement_date": date(2026, 1, 3),
                "movement_time": datetime(2026, 1, 3, 10, 0).time(),
                "notes": "test",
            }

    class FakeService:
        def get_portfolio_summary(self, portfolio_id, price_map):
            return {
                "remaining_cash": Decimal("1000"),
                "net_capital": Decimal("1200"),
            }

        def add_capital_movement(self, spec):
            calls.append(("service", {
                "portfolio_id": spec.portfolio_id,
                "movement_type": spec.movement_type,
                "amount": spec.amount,
                "movement_date": spec.movement_date,
                "movement_time": spec.movement_time,
                "notes": spec.notes,
            }))

    monkeypatch.setattr(
        "src.ui.pages.model_portfolio.utils.model_portfolio_actions.CapitalMovementDialog",
        FakeDialog,
    )
    monkeypatch.setattr(
        "src.ui.pages.model_portfolio.utils.model_portfolio_actions.Toast.success",
        lambda *args, **kwargs: None,
    )
    page = SimpleNamespace(
        current_portfolio_id=4,
        current_price_map={},
        model_portfolio_service=FakeService(),
        _load_portfolios=lambda: calls.append(("load",)),
        _update_view=lambda: calls.append(("update",)),
    )

    ModelPortfolioActions(page).on_capital_movement()

    assert calls[0] == ("dialog", Decimal("1000"), Decimal("1200"))
    assert calls[1][0] == "service"
    assert calls[1][1]["portfolio_id"] == 4
    assert calls[1][1]["movement_type"] == "DEPOSIT"
    assert calls[1][1]["amount"] == Decimal("500")
    assert ("load",) in calls
    assert ("update",) in calls


def test_model_portfolio_capital_action_ignores_invalid_dialog_result(monkeypatch):
    calls = []

    class FakeDialog:
        def __init__(self, current_cash, net_capital, parent=None):
            calls.append(("dialog", current_cash, net_capital))

        def exec(self):
            return QDialog.Accepted

        def get_result(self):
            return None

    class FakeService:
        def get_portfolio_summary(self, portfolio_id, price_map):
            return {
                "remaining_cash": Decimal("1000"),
                "net_capital": Decimal("1200"),
            }

        def add_capital_movement(self, spec):
            calls.append(("service", spec))

    monkeypatch.setattr(
        "src.ui.pages.model_portfolio.utils.model_portfolio_actions.CapitalMovementDialog",
        FakeDialog,
    )
    page = SimpleNamespace(
        current_portfolio_id=4,
        current_price_map={},
        model_portfolio_service=FakeService(),
        _load_portfolios=lambda: calls.append(("load",)),
        _update_view=lambda: calls.append(("update",)),
    )

    ModelPortfolioActions(page).on_capital_movement()

    assert calls == [("dialog", Decimal("1000"), Decimal("1200"))]


def test_model_portfolio_trade_action_blocks_closed_market_session(monkeypatch):
    warnings = []

    class FakeDialog:
        def __init__(self, parent=None, price_lookup_func=None, lot_size=1):
            self.btn_buy_mode = SimpleNamespace(setChecked=lambda val: None)
            self.btn_sell_mode = SimpleNamespace(setChecked=lambda val: None)

        def exec(self):
            return QDialog.Accepted

        def get_result(self):
            return {
                "ticker": "ASELS",
                "quantity": 1,
                "price": Decimal("10"),
                "trade_date": date(2026, 6, 6),
                "trade_time": time(11, 0),
                "side": "BUY",
            }

    class FakeService:
        def __init__(self):
            self.calls = []

        def add_trade_by_ticker(self, **kwargs):
            self.calls.append(kwargs)

    service = FakeService()
    page = SimpleNamespace(
        current_portfolio_id=4,
        price_lookup_func=None,
        market_session_service=SimpleNamespace(
            status_for=lambda trade_date, trade_time=None: SimpleNamespace(
                is_open=False,
                message="Kapali seans",
            )
        ),
        model_portfolio_service=service,
        _load_portfolios=lambda: None,
        _update_view=lambda: None,
    )
    monkeypatch.setattr(
        "src.ui.pages.model_portfolio.utils.model_portfolio_actions.NewStockTradeDialog",
        FakeDialog,
    )
    monkeypatch.setattr(
        "src.ui.pages.model_portfolio.utils.model_portfolio_actions.QMessageBox.warning",
        lambda *args, **kwargs: warnings.append(args[2]),
    )

    ModelPortfolioActions(page).on_trade()

    assert service.calls == []
    assert warnings
    assert "BIST" in warnings[0]


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
    page.price_data_health_service = None

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

    from src.ui.pages.model_portfolio.utils.portfolio_exporter import PortfolioExporter
    page.exporter = PortfolioExporter(page)
    page._on_export_today()

    assert export_service.calls[0][0:4] == (8, date(2026, 1, 2), date(2026, 5, 26), file_path)


def test_model_portfolio_export_today_blocks_when_history_prices_are_missing(monkeypatch):
    export_service = DummyModelPortfolioExcelExportService()
    warnings = []
    save_dialog_calls = []
    missing_report = PriceDataHealthReport(
        start_date=date(2026, 1, 2),
        end_date=date(2026, 6, 5),
        total_stock_count=1,
        expected_business_days=[date(2026, 6, 5)],
        weekend_days=[],
        empty_weekdays=[],
        holiday_candidate_dates=[],
        rows=[
            StockPriceHealthRow(
                stock_id=2,
                ticker="SMRTG.IS",
                last_price_date=date(2026, 6, 4),
                missing_dates=[date(2026, 6, 5)],
                first_missing_date=date(2026, 6, 5),
                last_missing_date=date(2026, 6, 5),
                status="Eksik Var",
                first_trade_date=date(2026, 1, 2),
            )
        ],
        latest_price_date=date(2026, 6, 4),
    )
    page = ModelPortfolioPage.__new__(ModelPortfolioPage)
    page.current_portfolio_id = 4
    page.lbl_portfolio_name = SimpleNamespace(text=lambda: "portföy-4")
    page.list_panel = SimpleNamespace(current_portfolio=lambda: ModelPortfolio(id=4, name="portföy-4"))
    page.model_portfolio_excel_export_service = export_service
    page.model_portfolio_service = SimpleNamespace(get_first_trade_date=lambda portfolio_id: date(2026, 1, 2))
    page.price_data_health_service = SimpleNamespace(
        analyze=lambda start_date, end_date, scope=None: missing_report
    )

    monkeypatch.setattr(
        "src.ui.pages.model_portfolio.utils.portfolio_exporter.date",
        SimpleNamespace(today=lambda: date(2026, 6, 5)),
    )
    monkeypatch.setattr(
        "src.ui.pages.model_portfolio.utils.portfolio_exporter.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: save_dialog_calls.append(args) or ("model.xlsx", "Excel Dosyaları (*.xlsx)"),
    )
    monkeypatch.setattr(
        "src.ui.pages.model_portfolio.utils.portfolio_exporter.QMessageBox.warning",
        lambda *args, **kwargs: warnings.append(args),
    )

    from src.ui.pages.model_portfolio.utils.portfolio_exporter import PortfolioExporter
    page.exporter = PortfolioExporter(page)
    page._on_export_today()

    assert export_service.calls == []
    assert save_dialog_calls == []
    assert warnings
    assert "SMRTG.IS" in warnings[0][2]
    assert "05.06.2026" in warnings[0][2]


def test_model_portfolio_report_menu_today_action_triggers_exporter():
    page = ModelPortfolioPage(
        container=SimpleNamespace(
            model_portfolio_service=EmptyModelPortfolioService(),
            price_repo=SimpleNamespace(),
            model_portfolio_excel_export_service=DummyModelPortfolioExcelExportService(),
        )
    )
    calls = []
    page.exporter = SimpleNamespace(
        export_today=lambda: calls.append("today"),
        export_range=lambda: calls.append("range"),
    )

    page._report_today_action.trigger()

    assert calls == ["today"]


def test_model_portfolio_report_menu_range_action_triggers_exporter():
    page = ModelPortfolioPage(
        container=SimpleNamespace(
            model_portfolio_service=EmptyModelPortfolioService(),
            price_repo=SimpleNamespace(),
            model_portfolio_excel_export_service=DummyModelPortfolioExcelExportService(),
        )
    )
    calls = []
    page.exporter = SimpleNamespace(
        export_today=lambda: calls.append("today"),
        export_range=lambda: calls.append("range"),
    )

    page._report_range_action.trigger()

    assert calls == ["range"]


def test_model_portfolio_refresh_publishes_prices_without_daily_price_write():
    price_repo = DummyPriceRepo()
    latest_price_repo = DummyLatestPriceRepo()
    event_signal = DummyEventSignal()
    from src.qt_compat.qtwidgets import QWidget
    page = ModelPortfolioPage.__new__(ModelPortfolioPage)
    QWidget.__init__(page)
    page.current_portfolio_id = 4
    page.model_portfolio_service = DummyModelPortfolioService()
    page.price_repo = price_repo
    page.latest_price_repo = latest_price_repo
    page.current_price_map = {}
    page.container = SimpleNamespace(event_bus=SimpleNamespace(prices_updated=event_signal))
    page.btn_refresh = QPushButton(" Fiyat Güncelle")
    page.price_lookup_func = lambda ticker: SimpleNamespace(
        price=Decimal("22.50"),
        as_of=datetime(2026, 4, 28, 12, 0),
        source="intraday",
    )
    page._update_view = lambda: None
    page.record_last_update_time = lambda: None
    page.show_last_update_toast_once = lambda **kwargs: None

    from src.ui.pages.model_portfolio.utils.portfolio_price_updater import PortfolioPriceUpdater
    page.price_updater = PortfolioPriceUpdater(page)
    page._actions = ModelPortfolioActions(page)
    def fake_start(worker):
        result = worker.fn()
        page._actions._on_update_prices_success(result)
    page.threadpool = SimpleNamespace(start=fake_start)

    page._actions.on_update_prices()

    assert price_repo.saved_prices == []
    assert [(item.stock_id, item.price, item.source) for item in latest_price_repo.saved_prices] == [
        (2, Decimal("22.50"), "intraday")
    ]
    assert event_signal.emitted == [{2: Decimal("22.50")}]


def test_model_portfolio_refresh_button_shows_updating_text_during_refresh(monkeypatch):
    event_signal = DummyEventSignal()
    process_events_calls = []
    from src.qt_compat.qtwidgets import QWidget
    page = ModelPortfolioPage.__new__(ModelPortfolioPage)
    QWidget.__init__(page)
    page.current_portfolio_id = 4
    page.model_portfolio_service = DummyModelPortfolioService()
    page.current_price_map = {}
    page.container = SimpleNamespace(event_bus=SimpleNamespace(prices_updated=event_signal))
    page.btn_refresh = QPushButton(" Fiyat Güncelle")
    page._update_view = lambda: None
    page.record_last_update_time = lambda: None
    page.show_last_update_toast_once = lambda **kwargs: None

    monkeypatch.setattr(
        "src.ui.pages.model_portfolio.model_portfolio_page.QApplication.processEvents",
        lambda: process_events_calls.append("processed"),
    )

    def lookup_price(ticker):
        assert process_events_calls == ["processed"]
        assert page.btn_refresh.text() == "Fiyatlar güncelleniyor..."
        assert not page.btn_refresh.isEnabled()
        return SimpleNamespace(
            price=Decimal("22.50"),
            as_of=datetime(2026, 4, 28, 12, 0),
            source="intraday",
        )

    page.price_lookup_func = lookup_price

    page.price_updater = SimpleNamespace(refresh_prices=lambda: (1, {2: Decimal("22.50")}))
    page._actions = ModelPortfolioActions(page)
    
    def fake_start(worker):
        assert page.btn_refresh.text() == "Fiyatlar güncelleniyor..."
        assert not page.btn_refresh.isEnabled()
        worker.signals.result.emit(worker.fn())
        worker.signals.finished.emit()

    page.threadpool = SimpleNamespace(start=fake_start)
    
    page._on_refresh_prices()

    assert page.btn_refresh.text() == " Fiyat Güncelle"
    assert page.btn_refresh.isEnabled()


def test_model_portfolio_prices_updated_event_updates_selected_portfolio_prices():
    from src.qt_compat.qtwidgets import QWidget
    page = ModelPortfolioPage.__new__(ModelPortfolioPage)
    QWidget.__init__(page)
    page.current_portfolio_id = 4
    page.model_portfolio_service = DummyModelPortfolioService()
    page.current_price_map = {2: Decimal("21.00")}
    calls = []

    page.settings_manager = SimpleNamespace(save_portfolio_last_update_time=lambda id, dt: None)

    page._presenter = ModelPortfolioPresenter(page)
    page._presenter.update_view = lambda: calls.append("updated")
    page._presenter.on_prices_updated_event(
        {
            2: Decimal("22.75"),
            99: Decimal("99.99"),
        },
    )

    assert page.current_price_map == {2: Decimal("22.75")}
    assert calls == ["updated"]

import sys
from datetime import date
from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")
from PyQt5.QtWidgets import QApplication

from src.application.services.market.price_data_health_service import (
    PriceDataHealthReport,
    PriceDataScopeOption,
    StockPriceHealthRow,
)
from src.ui.pages.settings import (
    AppearancePanel,
    CorporateActionCandidatesPanel,
    PriceDataPanel,
    ResetPanel,
)
from src.ui.pages.settings_page import SettingsPage
from src.ui.shared.live_price_refresh_controller import (
    LIVE_PRICE_REFRESH_ENABLED_KEY,
    LIVE_PRICE_REFRESH_INTERVAL_KEY,
)


app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class DummyResetService:
    def reset_all(self):
        pass


class DummyPriceDataHealthService:
    def minimum_start_date(self, scope=None):
        return {
            "all_active": date(2026, 1, 10),
            "dashboard": date(2026, 1, 15),
            "model:4": date(2026, 2, 1),
        }.get(scope or "all_active")

    def portfolio_scope_options(self):
        return [
            PriceDataScopeOption("all_active", "Tüm aktif portföyler"),
            PriceDataScopeOption("dashboard", "Ana Portföy"),
            PriceDataScopeOption("model:4", "Model Portföy: Büyüme"),
        ]

    def analyze(self, start_date, end_date, scope=None):
        return None

    def update_missing_prices(self, start_date, end_date, stock_ids=None, scope=None):
        return None

    def update_from_latest_to_today(self, today=None, scope=None):
        return None


class DummySettings:
    def __init__(self, organization=None, application=None):
        self.values = {}
        self.synced = False

    def value(self, key, default=None):
        return self.values.get(key, default)

    def setValue(self, key, value):
        self.values[key] = value

    def sync(self):
        self.synced = True


class DummyContainer:
    reset_service = DummyResetService()
    price_data_health_service = DummyPriceDataHealthService()
    event_bus = None
    corporate_action_discovery_service = None
    corporate_action_candidate_review_service = None
    stock_repo = None

    class trading_calendar:
        @staticmethod
        def is_trading_day(day):
            return day.weekday() < 5


def test_settings_page_renders_price_data_management_section(monkeypatch):
    monkeypatch.setattr("src.ui.pages.settings_page.QSettings", DummySettings)

    page = SettingsPage(container=DummyContainer())

    assert page.tabs.count() == 4
    assert page.tabs.tabText(0) == "Ana Sayfa"
    assert page.tabs.tabText(1) == "Görünüm"
    assert page.tabs.tabText(2) == "Fiyat Verisi Yönetimi"
    assert page.tabs.tabText(3) == "Kurumsal Aksiyonlar"
    assert page.btn_analyze.text().strip() == "Analiz Et"
    assert page.btn_update_missing.text().strip().startswith("Toplu Eksikleri")
    assert page.health_table.columnCount() == 6
    assert page.health_table.horizontalHeaderItem(0).text() == "Hisse"
    assert page.combo_portfolio_scope.currentData() == "all_active"
    assert page.combo_portfolio_scope.itemText(0) == "Tüm aktif portföyler"
    assert page.combo_portfolio_scope.itemText(2) == "Model Portföy: Büyüme"
    assert page.date_start.minimumDate().toPyDate() == date(2026, 1, 10)
    assert page.chk_live_price_refresh.text() == "Otomatik fiyat yenileme"
    assert page.chk_live_price_refresh.isChecked()
    assert page.combo_live_price_refresh_interval.currentData() == 15


def test_settings_page_keeps_proxy_surface():
    page = SettingsPage(container=DummyContainer())

    assert page.btn_analyze is page.price_data_tab.btn_analyze
    assert page.health_table is page.price_data_tab.health_table
    assert page.combo_portfolio_scope is page.price_data_tab.combo_portfolio_scope
    assert page.date_start is page.price_data_tab.date_start


def test_settings_page_live_price_refresh_controls_persist_without_restart(monkeypatch):
    settings = DummySettings()
    monkeypatch.setattr("src.ui.pages.settings_page.QSettings", lambda *args: settings)
    page = SettingsPage(container=DummyContainer())

    page.chk_live_price_refresh.setChecked(False)
    page.combo_live_price_refresh_interval.setCurrentIndex(
        page.combo_live_price_refresh_interval.findData(30)
    )

    assert settings.values[LIVE_PRICE_REFRESH_ENABLED_KEY] is False
    assert settings.values[LIVE_PRICE_REFRESH_INTERVAL_KEY] == 30
    assert settings.synced is True


def test_settings_panels_render_smoke():
    reset_panel = ResetPanel(DummyResetService())
    appearance_panel = AppearancePanel()
    price_data_panel = PriceDataPanel(DummyContainer(), DummyPriceDataHealthService())
    corporate_action_panel = CorporateActionCandidatesPanel(DummyContainer())

    assert reset_panel.btn_reset.text().strip().startswith("Sistemi")
    assert appearance_panel._theme_card_widgets
    assert price_data_panel.health_table.columnCount() == 6
    assert corporate_action_panel.table.columnCount() == 8


def test_settings_page_populates_health_table_from_report():
    page = SettingsPage(container=DummyContainer())
    report = PriceDataHealthReport(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 5),
        total_stock_count=2,
        expected_business_days=[date(2026, 1, 2), date(2026, 1, 5)],
        weekend_days=[date(2026, 1, 3), date(2026, 1, 4)],
        empty_weekdays=[],
        holiday_candidate_dates=[date(2026, 1, 5)],
        latest_price_date=date(2026, 1, 2),
        known_holiday_dates=[date(2026, 1, 1)],
        rows=[
            StockPriceHealthRow(
                stock_id=1,
                ticker="AAA.IS",
                last_price_date=date(2026, 1, 2),
                missing_dates=[],
                first_missing_date=None,
                last_missing_date=None,
                status="Saglikli",
            ),
            StockPriceHealthRow(
                stock_id=2,
                ticker="BBB.IS",
                last_price_date=date(2026, 1, 1),
                missing_dates=[date(2026, 1, 2)],
                first_missing_date=date(2026, 1, 2),
                last_missing_date=date(2026, 1, 2),
                status="Eksik Var",
            ),
        ],
    )

    page._apply_report(report)

    assert page.lbl_stock_count.metric_label.text() == "2"
    assert page.lbl_missing_count.metric_label.text() == "1"
    assert page.lbl_holiday_count.metric_label.text() == "1"
    assert page.lbl_holiday_candidate_count.metric_label.text() == "1"
    assert page.health_table.rowCount() == 2
    assert page.health_table.item(1, 0).text() == "BBB"
    assert page._selected_stock_id() is None


def test_report_without_known_holidays_backwards_compatible():
    report = PriceDataHealthReport(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 5),
        total_stock_count=0,
        expected_business_days=[],
        weekend_days=[],
        empty_weekdays=[],
        holiday_candidate_dates=[],
        rows=[],
        latest_price_date=None,
    )
    assert report.known_holiday_count == 0
    assert report.total_excluded_holiday_count == 0


def test_price_data_scope_change_updates_start_date_and_clears_report():
    page = SettingsPage(container=DummyContainer())
    page.detail_text.setText("Eski analiz")
    page._current_report = PriceDataHealthReport(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 5),
        total_stock_count=0,
        expected_business_days=[],
        weekend_days=[],
        empty_weekdays=[],
        holiday_candidate_dates=[],
        rows=[],
        latest_price_date=None,
    )

    page.combo_portfolio_scope.setCurrentIndex(page.combo_portfolio_scope.findData("model:4"))

    assert page.date_start.minimumDate().toPyDate() == date(2026, 2, 1)
    assert page._current_report is None
    assert page.detail_text.toPlainText() == "Analiz sonucu bekleniyor."


def test_price_data_actions_pass_selected_scope_to_workers():
    page = SettingsPage(container=DummyContainer())
    page.combo_portfolio_scope.setCurrentIndex(page.combo_portfolio_scope.findData("model:4"))
    calls = []

    def fake_run_worker(fn, success_slot, busy_text, *args):
        calls.append((fn.__name__, args))

    page.price_data_tab._actions._run_worker = fake_run_worker

    page.price_data_tab._actions.analyze()
    page.price_data_tab._actions.update_missing()

    assert calls[0] == ("analyze", (date(2026, 2, 1), page.date_end.date().toPyDate(), "model:4"))
    assert calls[1] == (
        "update_missing_prices",
        (date(2026, 2, 1), page.date_end.date().toPyDate(), None, "model:4"),
    )


def test_price_data_actions_update_from_latest_uses_last_completed_trading_day(monkeypatch):
    monkeypatch.setattr(
        "src.ui.pages.settings.utils.price_data_actions.date",
        SimpleNamespace(today=lambda: date(2026, 6, 8)),
    )
    page = SettingsPage(container=DummyContainer())
    page.combo_portfolio_scope.setCurrentIndex(page.combo_portfolio_scope.findData("model:4"))
    calls = []

    def fake_run_worker(fn, success_slot, busy_text, *args):
        calls.append((fn.__name__, args))

    page.price_data_tab._actions._run_worker = fake_run_worker

    page.price_data_tab._actions.update_from_latest()

    assert calls == [("update_from_latest_to_today", (date(2026, 6, 5), "model:4"))]

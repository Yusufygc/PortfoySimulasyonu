import sys
from datetime import date

import pytest

pytest.importorskip("PyQt5")
from PyQt5.QtWidgets import QApplication

from src.application.services.market.price_data_health_service import PriceDataHealthReport, StockPriceHealthRow
from src.ui.pages.settings_page import SettingsPage


app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class DummyResetService:
    def reset_all(self):
        pass


class DummyPriceDataHealthService:
    pass


class DummyContainer:
    reset_service = DummyResetService()
    price_data_health_service = DummyPriceDataHealthService()
    event_bus = None


def test_settings_page_renders_price_data_management_section():
    page = SettingsPage(container=DummyContainer())

    assert page.btn_analyze.text().strip() == "Analiz Et"
    assert page.btn_update_missing.text().strip() == "Toplu Eksikleri Güncelle"
    assert page.health_table.columnCount() == 6
    assert page.health_table.horizontalHeaderItem(0).text() == "Hisse"


def test_settings_page_populates_health_table_from_report():
    page = SettingsPage(container=DummyContainer())
    report = PriceDataHealthReport(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 5),
        total_stock_count=2,
        expected_business_days=[date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 5)],
        weekend_days=[date(2026, 1, 3), date(2026, 1, 4)],
        empty_weekdays=[],
        holiday_candidate_dates=[date(2026, 1, 5)],
        latest_price_date=date(2026, 1, 2),
        rows=[
            StockPriceHealthRow(
                stock_id=1,
                ticker="AAA.IS",
                last_price_date=date(2026, 1, 2),
                missing_dates=[],
                first_missing_date=None,
                last_missing_date=None,
                status="Sağlıklı",
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
    assert page.health_table.rowCount() == 2
    assert page.health_table.item(1, 0).text() == "BBB.IS"
    assert page._selected_stock_id() is None

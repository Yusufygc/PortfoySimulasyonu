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
    def minimum_start_date(self):
        return date(2026, 1, 10)


class DummyContainer:
    reset_service = DummyResetService()
    price_data_health_service = DummyPriceDataHealthService()
    event_bus = None


def test_settings_page_renders_price_data_management_section():
    page = SettingsPage(container=DummyContainer())

    assert page.tabs.count() == 3
    assert page.tabs.tabText(0) == "Ana Sayfa"
    assert page.tabs.tabText(1) == "Görünüm"
    assert page.tabs.tabText(2) == "Fiyat Verisi Yönetimi"
    assert page.btn_analyze.text().strip() == "Analiz Et"
    assert page.btn_update_missing.text().strip() == "Toplu Eksikleri Güncelle"
    assert page.health_table.columnCount() == 6
    assert page.health_table.horizontalHeaderItem(0).text() == "Hisse"
    assert page.date_start.minimumDate().toPyDate() == date(2026, 1, 10)


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
        # date(2026, 1, 1) is Yılbaşı — known holiday, excluded from expected_business_days
        known_holiday_dates=[date(2026, 1, 1)],
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
    assert page.lbl_holiday_count.metric_label.text() == "1"         # known holidays
    assert page.lbl_holiday_candidate_count.metric_label.text() == "1"  # heuristic candidates
    assert page.health_table.rowCount() == 2
    assert page.health_table.item(1, 0).text() == "BBB.IS"
    assert page._selected_stock_id() is None


def test_report_without_known_holidays_backwards_compatible():
    """known_holiday_dates alanı opsiyonel; eski kod default ile çalışmalı."""
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

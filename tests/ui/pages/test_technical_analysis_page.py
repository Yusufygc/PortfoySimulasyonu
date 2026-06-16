"""Teknik analiz UI sayfası testleri (PySide6)."""
from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("PySide6")
from src.qt_compat.qtwidgets import QApplication, QTableWidgetItem

from src.domain.models.golden_cross_event import CrossType, GoldenCrossEvent
from src.domain.models.stock import Stock
from src.application.services.analysis.technical.technical_analysis_service import ScanResult
from src.ui.pages.technical.technical_analysis_page import TechnicalAnalysisPage


app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class DummyTechnicalAnalysisService:
    def __init__(self):
        self.scanned = False
        self.recent_events_called = False

    def get_recent_events(self, days, cross_type=None, limit=200):
        self.recent_events_called = True
        return [
            GoldenCrossEvent(
                id=1, stock_id=1, ticker="ASELS",
                cross_date=date(2026, 6, 15),
                cross_type=CrossType.GOLDEN,
                short_ma=Decimal("50.5"), long_ma=Decimal("49.8"),
                close_price=Decimal("51.2")
            )
        ]

    def scan_all(self, today=None):
        self.scanned = True
        return ScanResult(1, 1, 0)

    def scan_ticker(self, ticker, today=None):
        return ScanResult(1, 1, 0)

    def get_events_for_ticker(self, ticker):
        return []


class DummyPriceRepo:
    def get_price_series(self, stock_id, start_date, end_date):
        return []


class DummyStockRepo:
    def get_stock_by_ticker(self, ticker):
        if ticker == "HATA":
            return None
        return Stock(id=1, ticker=ticker, name=ticker, currency_code="TRY")


class DummyPriceDataHealthService:
    def __init__(self):
        self.backfilled = False

    def update_from_latest_to_today(self, today=None, scope=None):
        self.backfilled = True
        return SimpleNamespace(updated_count=5)


class DummyContainer:
    def __init__(self):
        self.technical_analysis_service = DummyTechnicalAnalysisService()
        self.price_repo = DummyPriceRepo()
        self.stock_repo = DummyStockRepo()
        self.price_data_health_service = DummyPriceDataHealthService()
        self.trading_calendar = None


class TestTechnicalAnalysisPage:
    def test_page_renders_components(self):
        container = DummyContainer()
        page = TechnicalAnalysisPage(container=container)

        assert page.page_title == "Teknik Analiz"
        assert page._btn_scan.text() == "Taramayı Çalıştır"
        assert page._btn_backfill.text() == "Veri Tamamla"
        assert page._tabs.count() == 2
        assert page._tabs.tabText(0) == "Son Sinyaller"
        assert page._tabs.tabText(1) == "Ticker Detay"

        # Tablo basılmış olmalı
        assert page._tbl.rowCount() == 1
        assert page._tbl.item(0, 1).text() == "ASELS"
        assert "Golden" in page._tbl.item(0, 2).text()

    def test_scan_all_button_triggers_worker(self):
        container = DummyContainer()
        page = TechnicalAnalysisPage(container=container)

        # Mock self._pool.start to run synchronously or inspect worker
        workers_run = []
        def fake_start(worker):
            workers_run.append(worker)
            # simulate execution
            worker.run()

        page._pool.start = fake_start
        page._on_scan_all()

        assert container.technical_analysis_service.scanned is True
        assert page._btn_scan.isEnabled() is True
        assert page._btn_backfill.isEnabled() is True

    def test_backfill_all_button_triggers_worker(self):
        container = DummyContainer()
        page = TechnicalAnalysisPage(container=container)

        workers_run = []
        def fake_start(worker):
            workers_run.append(worker)
            worker.run()

        page._pool.start = fake_start
        page._on_backfill_all()

        assert container.price_data_health_service.backfilled is True
        assert page._btn_scan.isEnabled() is True
        assert page._btn_backfill.isEnabled() is True

    def test_table_double_click_switches_tab_and_loads_detail(self):
        container = DummyContainer()
        page = TechnicalAnalysisPage(container=container)

        # Set double click row
        page._on_row_double_clicked(0, 1)

        # Tab index 1'e geçmiş olmalı
        assert page._tabs.currentIndex() == 1
        assert page._ticker_edit.text() == "ASELS"

    def test_load_detail_data(self):
        container = DummyContainer()
        page = TechnicalAnalysisPage(container=container)

        data = page._load_detail_data("ASELS")
        assert data["ticker"] == "ASELS"
        assert isinstance(data["prices"], list)
        assert isinstance(data["events"], list)

        # Hatalı ticker durumunda boş liste dönmeli
        data_err = page._load_detail_data("HATA")
        assert data_err["prices"] == []

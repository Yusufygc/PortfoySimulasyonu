import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("PySide6")
from src.qt_compat.qtwidgets import QApplication

from src.application.services.analysis.technical.screener_service import ScreenerMatch
from src.ui.pages.screener import ScreenerPage

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


@pytest.fixture
def dummy_container():
    mock_screener = MagicMock()
    mock_screener.scan.return_value = [
        ScreenerMatch(ticker="THYAO", filter_key="rsi_oversold_above_ema200", filter_label="Aşırı Satım", close_price=290.5),
        ScreenerMatch(ticker="GARAN", filter_key="macd_bullish_cross_volume_spike", filter_label="MACD Bullish", close_price=115.2),
    ]
    mock_tech_service = MagicMock()
    mock_tech_service.get_recent_events.return_value = []
    mock_stock_repo = MagicMock()
    mock_stock_repo.get_stock_by_ticker.return_value = None
    mock_price_repo = MagicMock()
    mock_price_repo.get_price_series.return_value = []

    return SimpleNamespace(
        screener_service=mock_screener,
        technical_analysis_service=mock_tech_service,
        tv_backfill_service=None,
        stock_repo=mock_stock_repo,
        price_repo=mock_price_repo,
    )


def test_screener_page_init(dummy_container):
    page = ScreenerPage(container=dummy_container)
    assert page.page_title == "BIST Tarama"
    assert page._tabs.count() == 2
    assert "Çoklu Strateji" in page._tabs.tabText(0)
    assert "Teknik Analiz" in page._tabs.tabText(1)
    assert page._filter_combo.count() >= 3


def test_screener_page_scan_done(dummy_container):
    page = ScreenerPage(container=dummy_container)
    matches = [
        ScreenerMatch(ticker="AKBNK", filter_key="test", filter_label="Test Strateji", close_price=55.0)
    ]
    page._on_scan_done(matches)
    assert page._table.rowCount() == 1
    assert page._table.item(0, 0).text() == "AKBNK"
    assert page._table.item(0, 1).text() == "Test Strateji"


def test_screener_page_row_double_click_switches_to_technical_tab(dummy_container):
    page = ScreenerPage(container=dummy_container)
    matches = [
        ScreenerMatch(ticker="THYAO", filter_key="test", filter_label="Test Strateji", close_price=280.0)
    ]
    page._on_scan_done(matches)
    page._on_row_double_clicked(0, 0)

    assert page._tabs.currentIndex() == 1
    assert page._page_technical._current_ticker == "THYAO"

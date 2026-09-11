import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytest.importorskip("PySide6")
from src.qt_compat.qtwidgets import QApplication

from src.ui.pages.stock_360 import Stock360Page

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


@pytest.fixture
def dummy_container():
    mock_financial_service = MagicMock()
    mock_shareholder_service = MagicMock()
    mock_technical_service = MagicMock()
    mock_technical_service.get_recent_events.return_value = []
    mock_stock_repo = MagicMock()
    mock_stock_repo.get_stock_by_ticker.return_value = None
    mock_price_repo = MagicMock()
    mock_price_repo.get_price_series.return_value = []

    return SimpleNamespace(
        financial_analysis_service=mock_financial_service,
        shareholder_analysis_service=mock_shareholder_service,
        technical_analysis_service=mock_technical_service,
        tv_backfill_service=None,
        stock_repo=mock_stock_repo,
        price_repo=mock_price_repo,
    )


def test_stock_360_page_init(dummy_container):
    page = Stock360Page(container=dummy_container)
    assert page._tabs.count() == 2
    assert "Bilanço" in page._tabs.tabText(0)
    assert "Ortaklık" in page._tabs.tabText(1)


def test_stock_360_page_set_stock(dummy_container):
    page = Stock360Page(container=dummy_container)
    page.set_stock("THYAO")
    assert page._current_ticker == "THYAO"
    assert page._search_input.text() == "THYAO"


def test_stock_360_page_lifecycle(dummy_container):
    page = Stock360Page(container=dummy_container)
    page.on_page_enter()
    page.on_page_leave()

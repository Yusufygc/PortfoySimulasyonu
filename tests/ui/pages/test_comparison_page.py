import sys
import pytest

pytest.importorskip("PyQt5")
from PyQt5.QtWebEngineWidgets import QWebEngineView  # Must be imported before QApplication
from PyQt5.QtWidgets import QApplication

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from src.ui.pages.comparison.comparison_page import ComparisonPage
from src.ui.pages.comparison.widgets.ribbon_bar import ComparisonRibbonBar

class MockContainer:
    def __init__(self):
        class MockAnalysisService:
            def get_portfolio_options(self):
                return []
            def get_benchmark_definitions(self):
                return []
        self.analysis_service = MockAnalysisService()

def test_comparison_page_init():
    # Arrange
    container = MockContainer()
    
    # Act
    page = ComparisonPage(container)
    
    # Assert
    assert page.page_title == "Karşılaştırma Laboratuvarı"
    assert page.ribbon_bar is not None
    assert isinstance(page.ribbon_bar, ComparisonRibbonBar)
    assert page.main_chart_view is not None
    assert page.summary_table is not None
    from PyQt5.QtWidgets import QTableWidget
    assert isinstance(page.summary_table, QTableWidget)

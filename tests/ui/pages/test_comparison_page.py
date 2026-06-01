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
        class MockPortfolioOption:
            def __init__(self, code, label, kind):
                self.code = code
                self.label = label
                self.kind = kind
        class MockAnalysisService:
            def get_portfolio_options(self):
                return [MockPortfolioOption("dashboard", "Ana Portfoy", "dashboard")]
            def get_benchmark_definitions(self):
                return []
            def get_stock_map_for_source(self, code):
                return {}
            def get_first_trade_date_for_source(self, code):
                return None
            def get_comparison_view(self, filter_state):
                return None
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

def test_wheel_redirect_filter():
    # Arrange
    from PyQt5.QtCore import QPoint, QEvent, Qt, QCoreApplication
    from PyQt5.QtGui import QWheelEvent
    from PyQt5.QtWidgets import QScrollArea, QWidget
    from src.ui.pages.comparison.comparison_page import WheelRedirectFilter
    
    scroll_area = QScrollArea()
    filt = WheelRedirectFilter(scroll_area)
    
    widget = QWidget()
    widget.installEventFilter(filt)
    
    # Act & Assert
    pos = QPoint(10, 10)
    angle_delta = QPoint(0, -120)
    # Construct QWheelEvent: QWheelEvent(pos, globalPos, pixelDelta, angleDelta, angleDelta, orientation, buttons, modifiers)
    wheel_event = QWheelEvent(
        pos, pos, QPoint(), angle_delta, 120, Qt.Vertical, Qt.NoButton, Qt.NoModifier
    )
    
    # Intercept event and check that eventFilter returns True (meaning it consumed the event and forwarded it)
    res = filt.eventFilter(widget, wheel_event)
    assert res is True

def test_table_height_adjustment():
    # Arrange
    container = MockContainer()
    page = ComparisonPage(container)
    
    # Act
    page.summary_table.setRowCount(5)
    page._update_table_height()
    
    # Assert
    assert page.summary_table.minimumHeight() > 0
    assert page.summary_table.maximumHeight() == page.summary_table.minimumHeight()

def test_check_date_warnings(monkeypatch):
    from datetime import date, timedelta
    from PyQt5.QtCore import QDate
    
    class MockContainerForWarnings:
        def __init__(self):
            class MockAnalysisService:
                def get_portfolio_options(self):
                    return []
                def get_benchmark_definitions(self):
                    return []
                def get_first_trade_date_for_source(self, code):
                    return date(2026, 3, 15)
                def get_comparison_view(self, filter_state):
                    return None
            self.analysis_service = MockAnalysisService()
            
    container = MockContainerForWarnings()
    page = ComparisonPage(container)
    
    # Block signals to prevent _request_refresh from triggering worker during setup
    page.ribbon_bar.date_start.blockSignals(True)
    page.ribbon_bar.date_end.blockSignals(True)
    
    # 1. Test case: Start date after End date
    page.ribbon_bar.date_start.setDate(QDate(2026, 6, 1))
    page.ribbon_bar.date_end.setDate(QDate(2026, 5, 1))
    warnings = page._check_date_warnings()
    assert len(warnings) > 0
    assert "Başlangıç tarihi bitiş tarihinden sonra olamaz." in warnings[0]
    
    # 2. Test case: Start date before first trade date
    page.ribbon_bar.date_start.setDate(QDate(2026, 1, 1))
    page.ribbon_bar.date_end.setDate(QDate(2026, 5, 1))
    monkeypatch.setattr(page.ribbon_bar, "selected_assets", lambda: ["portfolio:4"])
    warnings = page._check_date_warnings()
    assert any("ilk işlem tarihinden" in w for w in warnings)
    
    # 3. Test case: End date in the future
    future_date = date.today() + timedelta(days=10)
    page.ribbon_bar.date_start.setDate(QDate(2026, 1, 1))
    page.ribbon_bar.date_end.setDate(QDate(future_date.year, future_date.month, future_date.day))
    warnings = page._check_date_warnings()
    assert any("bugünden ileri bir tarih olamaz" in w for w in warnings)


def test_chart_panel_init_and_update():
    from PyQt5.QtWidgets import QWidget
    from src.ui.pages.comparison.comparison_page import ChartPanel
    
    widget = QWidget()
    title = "Test Grafik"
    panel = ChartPanel(title, widget)
    
    assert panel.title_label.text() == title
    assert panel.inspect_btn is not None
    assert panel.inspect_btn.isHidden() is True
    
    selected_code = None
    def callback(code):
        nonlocal selected_code
        selected_code = code
        
    portfolio_options = [("Ana Portfoy", "dashboard"), ("Model A", "model:1")]
    panel.update_portfolio_options(portfolio_options, None, callback)
    
    assert panel.inspect_btn.isHidden() is False
    assert panel.inspect_btn.menu() is not None
    assert len(panel.actions) == 3
    
    # Trigger the second action (first portfolio selection)
    panel.actions[1].trigger()
    assert selected_code == "dashboard"


def test_compare_portfolio_holdings(monkeypatch):
    container = MockContainer()
    stock_map = {1: "THYAO.IS", 2: "EREGL.IS"}
    # Mock method in analysis_service
    monkeypatch.setattr(container.analysis_service, "get_stock_map_for_source", lambda code: stock_map)
    
    page = ComparisonPage(container)
    
    # Select holdings option in ribbon_bar
    page.ribbon_bar.set_selected_assets(["holdings:dashboard"])
    
    # Call _request_refresh which will intercept holdings:dashboard
    page._request_refresh()
    
    # Assert ribbon_bar has the stocks selected along with the portfolio
    selected = page.ribbon_bar.selected_assets()
    assert "dashboard" in selected
    assert "1" in selected
    assert "2" in selected


def test_chart_specific_override():
    container = MockContainer()
    page = ComparisonPage(container)
    
    # Set an override for main_chart
    page.handle_chart_portfolio_selected("main_chart", "dashboard")
    assert page.chart_overrides.get("main_chart") == "dashboard"
    
    # Set it back to None (Küresel Seçime Dön)
    page.handle_chart_portfolio_selected("main_chart", None)
    assert page.chart_overrides.get("main_chart") is None





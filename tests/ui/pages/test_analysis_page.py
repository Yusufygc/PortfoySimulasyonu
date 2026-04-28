import sys
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")
from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QApplication, QGridLayout, QSizePolicy

from src.application.services.analysis import ComparisonViewDTO
from src.ui.pages.analysis import AnalysisPage
from src.ui.pages.analysis.analysis_chart_engine import AnalysisChartEngine
from src.ui.pages.analysis.analysis_comparison_section import AnalysisComparisonSection
from src.ui.pages.analysis.analysis_control_panel import AnalysisControlPanel
from src.ui.pages.analysis.analysis_overview_section import AnalysisOverviewSection
from src.ui.pages.analysis.benchmark_chip_group import BenchmarkChipGroup
from src.ui.pages.analysis.checkable_combo_box import CheckableComboBox
from src.ui.theme_manager import ThemeManager


app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class DummyAnalysisService:
    def get_portfolio_options(self):
        return []

    def get_stock_map_for_source(self, source):
        return {}

    def get_first_trade_date_for_source(self, source):
        return None

    def get_benchmark_definitions(self):
        return []


class DummyPortfolioService:
    def get_first_trade_date(self):
        return None


def test_analysis_page_has_three_primary_tabs():
    container = SimpleNamespace(
        analysis_service=DummyAnalysisService(),
        portfolio_service=DummyPortfolioService(),
    )

    page = AnalysisPage(container=container)

    assert page.tabs.count() == 3
    assert page.tabs.tabText(0) == "Genel Bak\u0131\u015f"
    assert page.tabs.tabText(1) == "Kar\u015f\u0131la\u015ft\u0131rma"
    assert page.tabs.tabText(2) == "Da\u011f\u0131l\u0131m & Risk"


def test_analysis_page_keeps_filter_panel_in_a_full_height_right_column():
    container = SimpleNamespace(
        analysis_service=DummyAnalysisService(),
        portfolio_service=DummyPortfolioService(),
    )

    page = AnalysisPage(container=container)
    tab_bar = page.tabs.tabBar()

    assert page.control_panel_scroll.widget() is page.control_panel
    assert page.control_panel_scroll.widgetResizable() is True
    assert page.control_panel_scroll.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    assert page.control_panel_scroll.minimumWidth() == page.control_panel.minimumWidth() + 20
    assert page.control_panel_scroll.maximumWidth() == page.control_panel.maximumWidth() + 20
    assert page.control_panel_column.layout().itemAt(0).widget() is page.control_panel_scroll
    assert page.control_panel_scroll.sizePolicy().verticalPolicy() == QSizePolicy.Expanding
    assert page.control_panel.sizePolicy().verticalPolicy() == QSizePolicy.Expanding
    assert page.btn_refresh.parentWidget() is not page
    assert page.control_panel.minimumWidth() == 500
    assert tab_bar.expanding() is True
    assert tab_bar.usesScrollButtons() is False
    assert tab_bar.elideMode() == Qt.ElideNone


def test_checkable_combo_box_toggles_items_from_popup_view():
    combo = CheckableComboBox()
    combo.set_items([("Ana Portf\u00f6y", "main"), ("Model Portf\u00f6y", "model")])
    combo.resize(240, 38)
    combo.showPopup()
    view = combo.popup_view()

    index = combo.model().index(0, 0)
    point = view.visualRect(index).center()
    event = QMouseEvent(
        QEvent.MouseButtonRelease,
        point,
        point,
        point,
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier,
    )

    assert combo.eventFilter(view.viewport(), event) is True
    assert combo.selected_data() == ["main"]
    assert combo.lineEdit().text() == "Ana Portf\u00f6y"


def test_checkable_combo_box_popup_has_minimum_geometry():
    combo = CheckableComboBox()
    combo.set_items([("Ana Portf\u00f6y", "main"), ("Model Portf\u00f6y", "model")])
    combo.resize(220, 38)

    combo.showPopup()
    view = combo.popup_view()

    assert view.minimumWidth() >= 300
    assert view.minimumHeight() > 0


def test_checkable_combo_box_ignores_deleted_popup_view():
    class DeletedPopupView:
        def viewport(self):
            raise RuntimeError("wrapped C/C++ object of type QListView has been deleted")

    combo = CheckableComboBox()
    combo._popup_view = DeletedPopupView()

    assert combo.eventFilter(object(), QEvent(QEvent.MouseButtonRelease)) is False


def test_control_panel_places_stock_filter_below_comparison_portfolios():
    panel = AnalysisControlPanel()
    layout = panel.layout()
    stock_frame = layout.itemAt(3).widget()
    stock_layout = stock_frame.layout()

    assert stock_layout.itemAt(stock_layout.count() - 1).widget() is panel.stock_combo
    assert stock_layout.itemAt(0).widget().text() == "Hisse Filtresi"


def test_control_panel_populates_comparison_and_stock_items():
    panel = AnalysisControlPanel()
    options = [
        SimpleNamespace(code="dashboard", label="Ana Portf\u00f6y"),
        SimpleNamespace(code="model:1", label="Portf\u00f6y 1"),
        SimpleNamespace(code="model:2", label="Portf\u00f6y 2"),
    ]

    panel.set_portfolio_options(options)
    panel.set_comparison_portfolios(options)
    panel.set_stocks({1: "ASELS.IS", 2: "THYAO.IS"})

    assert panel.compare_combo.model().rowCount() == 2
    assert panel.stock_combo.model().rowCount() == 2


def test_overview_section_uses_wrapped_warning_banner_and_metric_grid():
    section = AnalysisOverviewSection()
    metrics_layout = section.layout().itemAt(1).layout()

    assert section.warning_banner.wordWrap() is True
    assert isinstance(metrics_layout, QGridLayout)


def test_checkable_combo_box_popup_layout_resolves_inside_analysis_page():
    ThemeManager.apply_theme(app, "dark_theme")
    container = SimpleNamespace(
        analysis_service=DummyAnalysisService(),
        portfolio_service=DummyPortfolioService(),
    )
    page = AnalysisPage(container=container)
    page.control_panel.set_portfolio_options(
        [
            SimpleNamespace(code="dashboard", label="Ana Portföy"),
            SimpleNamespace(code="model:1", label="Portföy 1"),
            SimpleNamespace(code="model:2", label="Portföy 2"),
        ]
    )
    page.control_panel.set_comparison_portfolios(
        [
            SimpleNamespace(code="dashboard", label="Ana Portföy"),
            SimpleNamespace(code="model:1", label="Portföy 1"),
            SimpleNamespace(code="model:2", label="Portföy 2"),
        ]
    )
    page.resize(1400, 900)
    page.show()
    app.processEvents()

    combo = page.control_panel.compare_combo
    combo.showPopup()
    app.processEvents()
    view = combo.popup_view()

    first_rect = view.visualRect(combo.model().index(0, 0))
    assert first_rect.height() > 0
    assert first_rect.width() > 0
    assert view.isVisible() is True


def test_benchmark_chip_group_reserves_height_for_all_rows():
    group = BenchmarkChipGroup()
    definitions = [
        SimpleNamespace(code="bist100", label="BIST 100"),
        SimpleNamespace(code="gold", label="Alt\u0131n"),
        SimpleNamespace(code="usdtry", label="USD/TRY"),
        SimpleNamespace(code="faiz", label="Mevduat Faizi"),
    ]

    group.set_benchmarks(definitions)

    assert group.minimumHeight() >= group.layout().sizeHint().height()
    assert group.layout().itemAtPosition(0, 3) is not None
    assert group.layout().itemAtPosition(1, 0) is None
    assert "\n" in group.layout().itemAtPosition(0, 3).widget().text()


def test_chart_engine_trims_leading_zero_points_for_normalized_series():
    chart = AnalysisChartEngine(show_toolbar=False)

    chart.draw_line_series(
        "Test",
        "Normalize Değer",
        {
            "Ana Portföy": {
                date(2026, 1, 1): Decimal("0"),
                date(2026, 1, 2): Decimal("50"),
                date(2026, 1, 3): Decimal("75"),
            }
        },
        normalize=True,
        baseline=100,
    )

    series = chart._prepared_series[0]
    assert series.trimmed_points == 1
    assert series.y_values == [100.0, 150.0]
    assert len(series.x_values) == 2
    assert "başlangıç noktası kırpıldı" in chart.lbl_summary.text()


def test_chart_engine_draws_empty_state_for_all_zero_normalized_series():
    chart = AnalysisChartEngine(show_toolbar=False)

    chart.draw_line_series(
        "Test",
        "Normalize Değer",
        {
            "Boş Portföy": {
                date(2026, 1, 1): Decimal("0"),
                date(2026, 1, 2): Decimal("0"),
            }
        },
        normalize=True,
        baseline=100,
    )

    assert chart._prepared_series == []
    assert chart.lbl_summary.text() == "Veri bulunamadı"


def test_chart_engine_marks_first_series_as_primary():
    chart = AnalysisChartEngine(show_toolbar=False)

    chart.draw_line_series(
        "Test",
        "Normalize Değer",
        {
            "Ana Portföy": {date(2026, 1, 1): Decimal("100"), date(2026, 1, 2): Decimal("105")},
            "BIST 100": {date(2026, 1, 1): Decimal("100"), date(2026, 1, 2): Decimal("102")},
        },
        normalize=True,
        baseline=100,
    )

    assert chart._prepared_series[0].is_primary is True
    assert chart._prepared_series[0].label == "Ana Portföy"
    assert chart._prepared_series[1].is_primary is False


def test_chart_engine_disables_si_prefix_on_date_axis():
    chart = AnalysisChartEngine(show_toolbar=False)
    bottom_axis = chart.plot_widget.getPlotItem().getAxis("bottom")

    assert getattr(bottom_axis, "autoSIPrefix", None) is False


def test_chart_engine_pie_uses_slice_labels_without_side_legend():
    chart = AnalysisChartEngine(show_toolbar=False)

    chart.draw_portfolio_pie("Dağılım", [("ASELS.IS", 60.0), ("THYAO.IS", 40.0)])

    assert chart.pie_widget.isHidden() is False
    assert chart.legend_panel.isHidden() is True
    assert chart.legend_layout.count() == 0


def test_comparison_section_can_draw_stocks_without_portfolio_series():
    class SpyChartEngine:
        def __init__(self):
            self.last_call = None

        def draw_line_series(self, **kwargs):
            self.last_call = ("line", kwargs)

        def draw_empty_chart(self, message):
            self.last_call = ("empty", message)

    section = AnalysisComparisonSection()
    spy = SpyChartEngine()
    section.chart_engine = spy
    section._dto = ComparisonViewDTO(
        portfolio_series={date(2026, 1, 1): Decimal("100")},
        benchmark_series=[],
        stock_series={
            "ASELS.IS": {date(2026, 1, 1): Decimal("10"), date(2026, 1, 2): Decimal("11")},
            "THYAO.IS": {date(2026, 1, 1): Decimal("20"), date(2026, 1, 2): Decimal("19")},
        },
        comparison_metrics=[],
        comparison_portfolios=[],
        current_portfolio_label="Ana Portföy",
        warnings=[],
    )

    section.combo_mode.setCurrentIndex(section.combo_mode.findData(section.MODE_STOCKS_ONLY))
    section._redraw_chart()

    call_type, kwargs = spy.last_call
    assert call_type == "line"
    assert kwargs["title"] == "Seçili Hisseler Karşılaştırması"
    assert list(kwargs["series_map"].keys()) == ["ASELS.IS", "THYAO.IS"]
    assert "Ana Portföy" not in kwargs["series_map"]

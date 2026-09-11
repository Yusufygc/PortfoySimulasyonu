import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
import plotly.graph_objects as go

pytest.importorskip("PySide6")
from src.qt_compat.qtcore import QDate, Qt
from src.qt_compat.qtwebengine import QWebEngineView  # Must be imported before QApplication
from src.qt_compat.qtwidgets import QApplication, QGridLayout, QHBoxLayout, QSizePolicy

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from src.ui.pages.comparison.comparison_page import ComparisonPage
from src.ui.pages.comparison.widgets.ribbon_bar import ComparisonRibbonBar
from src.ui.shared.locale_tr import L10N

class MockContainer:
    def __init__(self):
        self.first_trade_dates = {}
        class MockPortfolioOption:
            def __init__(self, code, label, kind):
                self.code = code
                self.label = label
                self.kind = kind
        class MockAnalysisService:
            def __init__(self, outer):
                self._outer = outer
            def get_portfolio_options(self):
                return [MockPortfolioOption("dashboard", "Ana Portfoy", "dashboard")]
            def get_benchmark_definitions(self):
                return []
            def get_stock_map_for_source(self, code):
                return {}
            def get_first_trade_date_for_source(self, code):
                return self._outer.first_trade_dates.get(code)
            def get_comparison_view(self, filter_state):
                return None
        self.analysis_service = MockAnalysisService(self)
        self.ai_chat_service = SimpleNamespace(generate=lambda messages: "")

def test_comparison_page_init():
    # Arrange
    container = MockContainer()
    
    # Act
    page = ComparisonPage(container)
    
    # Assert
    assert page.page_title == "Karşılaştırma Laboratuvarı"
    assert page.ribbon_bar is not None
    assert isinstance(page.ribbon_bar, ComparisonRibbonBar)
    assert page._main_chart_view is None
    assert page.main_chart_placeholder is not None
    assert page.summary_table is not None
    from src.qt_compat.qtwidgets import QTableWidget
    assert isinstance(page.summary_table, QTableWidget)


def test_empty_comparison_does_not_create_blank_webengine_view():
    page = ComparisonPage(MockContainer())

    page._data_manager.request_refresh()
    page._view_manager.check_viewport_visibility()

    assert page._main_chart_view is None
    assert page.last_global_df is None
    assert page.main_chart_placeholder.label.text() == L10N.LUTFEN_KIYASLANACAK_VARLIKLARI_SECIN


def test_empty_state_updates_existing_view_with_dark_html():
    page = ComparisonPage(MockContainer())

    class FakeView:
        def __init__(self):
            self.html = ""

        def setHtml(self, html):
            self.html = html

    fake_view = FakeView()
    page._main_chart_view = fake_view

    page._renderer.render_empty_state(L10N.LUTFEN_KIYASLANACAK_VARLIKLARI_SECIN)

    assert "background-color:#0f172a" in fake_view.html
    assert L10N.LUTFEN_KIYASLANACAK_VARLIKLARI_SECIN in fake_view.html


def test_data_ready_clears_empty_state_and_triggers_render(monkeypatch):
    from src.ui.pages.comparison.utils import comparison_data_manager

    page = ComparisonPage(MockContainer())
    df = pd.DataFrame(
        {"Ana Portfoy": [100.0, 102.0]},
        index=pd.to_datetime(["2026-06-01", "2026-06-02"]),
    )
    rendered = []

    monkeypatch.setattr(
        comparison_data_manager.ComparisonSeriesBuilder,
        "build_global_series",
        staticmethod(lambda dto, selected_sids: ({"Ana Portfoy": df["Ana Portfoy"]}, {})),
    )
    monkeypatch.setattr(
        comparison_data_manager.ComparisonService,
        "align_financial_series",
        staticmethod(lambda series_dict: df),
    )
    monkeypatch.setattr(page._renderer, "trigger_visible_charts_render", lambda data: rendered.append(data))

    page._comparison_empty_message = L10N.LUTFEN_KIYASLANACAK_VARLIKLARI_SECIN
    page._request_seq = 1
    page._data_manager._on_data_ready(1, object())

    assert page._comparison_empty_message is None
    assert page.last_global_df is df
    assert rendered == [df]


def test_chart_renderer_cleanup_stops_pending_loads(tmp_path):
    page = ComparisonPage(MockContainer())
    temp_file = tmp_path / "queued.html"
    temp_file.write_text("<html></html>", encoding="utf-8")
    page._renderer._load_queue.append((object(), str(temp_file)))
    page._renderer._load_timer.start(1000)

    page._renderer.cleanup()

    assert not page._renderer._load_timer.isActive()
    assert page._renderer._load_queue == []
    assert not temp_file.exists()

def test_wheel_redirect_filter():
    # Arrange
    from src.qt_compat.qtcore import QPoint, Qt
    from src.qt_compat.qtgui import QWheelEvent
    from src.qt_compat.qtwidgets import QScrollArea, QWidget
    from src.ui.pages.comparison.comparison_page import WheelRedirectFilter
    
    scroll_area = QScrollArea()
    scroll_area.verticalScrollBar().setRange(0, 1000)
    scroll_area.verticalScrollBar().setValue(100)
    filt = WheelRedirectFilter(scroll_area)
    
    widget = QWidget()
    widget.installEventFilter(filt)
    
    # Act & Assert
    pos = QPoint(10, 10)
    angle_delta = QPoint(0, -120)
    # Construct QWheelEvent with the Qt6 signature.
    wheel_event = QWheelEvent(
        pos,
        pos,
        QPoint(),
        angle_delta,
        Qt.NoButton,
        Qt.NoModifier,
        Qt.ScrollUpdate,
        False,
    )
    
    res = filt.eventFilter(widget, wheel_event)
    assert res is True
    assert scroll_area.verticalScrollBar().value() > 100

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


def test_ribbon_uses_left_right_block_layout():
    ribbon = ComparisonRibbonBar()

    assert isinstance(ribbon.controls_layout, QHBoxLayout)
    assert isinstance(ribbon.left_grid, QGridLayout)
    assert ribbon.controls_layout.indexOf(ribbon.left_container) >= 0
    assert ribbon.controls_layout.indexOf(ribbon.right_container) >= 0
    assert ribbon.left_container.property("cssClass") == "comparisonFilterBlock"
    assert ribbon.right_container.property("cssClass") == "comparisonFilterBlock"
    assert ribbon.ratio_label.isHidden() is True
    assert ribbon.combo_num.isHidden() is True
    assert ribbon.ratio_den_label.isHidden() is True
    assert ribbon.combo_den.isHidden() is True

    assert ribbon.left_grid.getItemPosition(ribbon.left_grid.indexOf(ribbon.compare_combo))[:2] == (0, 1)
    assert ribbon.left_grid.getItemPosition(ribbon.left_grid.indexOf(ribbon.combo_num))[:2] == (1, 1)
    assert ribbon.left_grid.getItemPosition(ribbon.left_grid.indexOf(ribbon.combo_mode))[:2] == (0, 3)
    assert ribbon.left_grid.getItemPosition(ribbon.left_grid.indexOf(ribbon.combo_den))[:2] == (1, 3)

    ribbon.combo_mode.setCurrentText(L10N.RASYO_MODU)

    assert ribbon.ratio_label.isHidden() is False
    assert ribbon.combo_num.isHidden() is False
    assert ribbon.ratio_den_label.isHidden() is False
    assert ribbon.combo_den.isHidden() is False
    assert ribbon.date_row.indexOf(ribbon.date_start) >= 0
    assert ribbon.date_row.indexOf(ribbon.date_end) >= 0
    assert ribbon.date_start.displayFormat() == "dd.MM.yyyy"
    assert ribbon.date_end.displayFormat() == "dd.MM.yyyy"
    assert ribbon.date_start.minimumWidth() >= 138
    assert ribbon.date_end.minimumWidth() >= 138
    assert ribbon.right_vbox.indexOf(ribbon.date_row) >= 0
    assert ribbon.right_vbox.indexOf(ribbon.time_buttons_layout) >= 0
    for label, button in ribbon.time_buttons.items():
        assert label in {"1A", "3A", "6A", "1Y", "YBB", "Tümü"}
        assert ribbon.time_buttons_layout.indexOf(button) >= 0
    assert ribbon.combo_num.minimumWidth() >= 220
    assert ribbon.combo_den.minimumWidth() >= 220
    assert ribbon.combo_num.sizePolicy().horizontalPolicy() == QSizePolicy.Expanding
    assert ribbon.combo_den.sizePolicy().horizontalPolicy() == QSizePolicy.Expanding

    positions_after_ratio = {
        "num": ribbon.left_grid.getItemPosition(ribbon.left_grid.indexOf(ribbon.combo_num))[:2],
        "den": ribbon.left_grid.getItemPosition(ribbon.left_grid.indexOf(ribbon.combo_den))[:2],
    }
    ribbon.combo_mode.setCurrentText("Normal")
    ribbon.combo_mode.setCurrentText(L10N.RASYO_MODU)
    assert positions_after_ratio == {
        "num": ribbon.left_grid.getItemPosition(ribbon.left_grid.indexOf(ribbon.combo_num))[:2],
        "den": ribbon.left_grid.getItemPosition(ribbon.left_grid.indexOf(ribbon.combo_den))[:2],
    }


def test_ribbon_set_selected_assets_emits_once_and_can_be_silent():
    ribbon = ComparisonRibbonBar()
    ribbon.set_assets([("Ana Portfoy", "dashboard"), ("BIST100", "bist100")])
    emissions = []
    ribbon.filter_changed.connect(lambda: emissions.append("changed"))

    ribbon.set_selected_assets(["dashboard"])

    assert emissions == ["changed"]

    ribbon.set_selected_assets(["dashboard", "bist100"], emit=False)

    assert emissions == ["changed"]
    assert ribbon.selected_assets() == ["dashboard", "bist100"]


def test_all_range_uses_selected_portfolio_first_trade_date():
    container = MockContainer()
    container.first_trade_dates = {
        "dashboard": date(2018, 5, 10),
        "model:4": date(2020, 1, 2),
    }
    page = ComparisonPage(container)
    page.ribbon_bar.set_assets([("Ana Portfoy", "dashboard"), ("Model", "model:4")])
    page.ribbon_bar.set_selected_assets(["dashboard", "model:4"])

    page.ribbon_bar._on_time_button_clicked("TÃ¼mÃ¼", None)

    all_label = next(label for label in page.ribbon_bar.time_buttons if label.startswith("T"))
    page.ribbon_bar._on_time_button_clicked(all_label, None)

    assert page.ribbon_bar.date_start.date().toPyDate() == date(2018, 5, 10)
    assert page.ribbon_bar.date_end.date() == QDate.currentDate()


def test_all_range_falls_back_to_2000_without_portfolio_selection():
    page = ComparisonPage(MockContainer())
    page.ribbon_bar.set_assets([("BIST100", "benchmark:XU100")])
    page.ribbon_bar.set_selected_assets([])

    page.ribbon_bar._on_time_button_clicked("TÃ¼mÃ¼", None)

    all_label = next(label for label in page.ribbon_bar.time_buttons if label.startswith("T"))
    page.ribbon_bar._on_time_button_clicked(all_label, None)

    assert page.ribbon_bar.date_start.date().toPyDate() == date(2000, 1, 1)


def test_main_info_card_updates_with_graph_mode():
    page = ComparisonPage(MockContainer())

    page.ribbon_bar.combo_mode.setCurrentText("Normal")
    normal_text = page.main_info_card.label.text()
    assert "Grafik Modu yalnızca bu ana performans grafiğinin çizim mantığını değiştirir" in normal_text
    assert "kümülatif getiri gelişimini" in normal_text
    assert page.main_info_card.property("cssState") == "normal"

    page.ribbon_bar.combo_mode.setCurrentText(L10N.RASYO_MODU)
    ratio_text = page.main_info_card.label.text()
    assert "göreli gücünü" in ratio_text
    assert "Pay kısmındaki varlığın" in ratio_text
    assert "yalnızca bu ana performans grafiğinde geçerlidir" in ratio_text
    assert page.main_info_card.property("cssState") == "ratio"

    page.ribbon_bar.combo_mode.setCurrentText(L10N.NORMALIZE_BAZ_100)
    normalize_text = page.main_info_card.label.text()
    assert "başlangıç değerlerini 100'e eşitleyerek göreli performans gelişimini" in normalize_text
    assert "göreli güç ve sapma daha net kıyaslanır" in normalize_text
    assert "Grafik Modu yalnızca bu ana performans grafiğinin çizim mantığını değiştirir" in normalize_text
    assert page.main_info_card.property("cssState") == "normal"


def test_sub_chart_info_cards_state_scope_is_static_across_mode_changes():
    page = ComparisonPage(MockContainer())

    drawdown_text = page.drawdown_info_card.label.text()
    periodic_text = page.periodic_info_card.label.text()
    scatter_text = page.scatter_info_card.label.text()
    treemap_text = page.treemap_info_card.label.text()

    assert "Grafik Modu bu grafiği değiştirmez" in drawdown_text
    assert "Grafik Modu bu grafiği değiştirmez" in periodic_text
    assert "Grafik Modu bu grafiği değiştirmez" in scatter_text
    assert "Grafik Modu bu grafiği değiştirmez" in treemap_text

    page.ribbon_bar.combo_mode.setCurrentText(L10N.RASYO_MODU)

    assert page.drawdown_info_card.label.text() == drawdown_text
    assert page.periodic_info_card.label.text() == periodic_text
    assert page.scatter_info_card.label.text() == scatter_text
    assert page.treemap_info_card.label.text() == treemap_text


def test_ai_browser_expands_to_content_without_internal_scroll():
    page = ComparisonPage(MockContainer())
    browser = page.ai_browser
    initial_height = browser.minimumHeight()

    long_markdown = "\n\n".join([f"Paragraf {idx}: uzun analiz metni." for idx in range(80)])
    browser.setMarkdown(long_markdown)
    page.ai_helper._fit_ai_browser_to_content()

    assert browser.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    assert browser.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    assert browser.sizePolicy().horizontalPolicy() == QSizePolicy.Preferred
    assert browser.sizePolicy().verticalPolicy() == QSizePolicy.Expanding
    assert browser.minimumHeight() > initial_height

def test_check_date_warnings(monkeypatch, fixed_today):
    from datetime import date, timedelta
    from src.qt_compat.qtcore import QDate
    from src.ui.pages.comparison.utils import comparison_warning_builder

    class FixedDate(date):
        @classmethod
        def today(cls):
            return fixed_today

    monkeypatch.setattr(comparison_warning_builder, "date", FixedDate)
    
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
            self.ai_chat_service = SimpleNamespace(generate=lambda messages: "")

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
    future_date = fixed_today + timedelta(days=10)
    page.ribbon_bar.date_start.setDate(QDate(2026, 1, 1))
    page.ribbon_bar.date_end.setDate(QDate(future_date.year, future_date.month, future_date.day))
    warnings = page._check_date_warnings()
    assert any("bugünden ileri bir tarih olamaz" in w for w in warnings)


def test_chart_panel_init_and_update():
    from src.qt_compat.qtwidgets import QWidget
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


def test_holdings_expansion_does_not_emit_second_refresh(monkeypatch):
    class CapturingThreadPool:
        def __init__(self):
            self.started = []

        def start(self, worker):
            self.started.append(worker)

    container = MockContainer()
    monkeypatch.setattr(container.analysis_service, "get_stock_map_for_source", lambda code: {1: "THYAO.IS", 2: "EREGL.IS"})
    page = ComparisonPage(container)
    threadpool = CapturingThreadPool()
    page._data_manager.threadpool = threadpool

    page.ribbon_bar.set_selected_assets(["holdings:dashboard"])

    assert len(threadpool.started) == 1
    assert {"dashboard", "1", "2"}.issubset(set(page.ribbon_bar.selected_assets()))


def test_request_refresh_restores_scroll_position_after_layout_updates(monkeypatch, qapp):
    class CapturingThreadPool:
        def __init__(self):
            self.started = []

        def start(self, worker):
            self.started.append(worker)

    page = ComparisonPage(MockContainer())
    page._data_manager.threadpool = CapturingThreadPool()
    page.ribbon_bar.set_selected_assets(["dashboard"], emit=False)
    scroll_bar = page.scroll_area.verticalScrollBar()
    scroll_bar.setRange(0, 1000)
    scroll_bar.setValue(345)

    def jump_during_panel_refresh():
        scroll_bar.setValue(0)

    monkeypatch.setattr(page._data_manager, "refresh_panel_options", jump_during_panel_refresh)

    page._request_refresh()
    qapp.processEvents()

    assert scroll_bar.value() == 345


def test_chart_specific_override():
    container = MockContainer()
    page = ComparisonPage(container)
    
    # Set an override for main_chart
    page.handle_chart_portfolio_selected("main_chart", "dashboard")
    assert page.chart_overrides.get("main_chart") == "dashboard"
    
    # Set it back to None (Küresel Seçime Dön)
    page.handle_chart_portfolio_selected("main_chart", None)
    assert page.chart_overrides.get("main_chart") is None


def test_chart_renderer_writes_plotly_html_and_loads_local_file(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from src.ui.pages.comparison.utils import chart_renderer

    class FakeView:
        def __init__(self):
            self.loaded_url = None

        def load(self, url):
            self.loaded_url = url

    shared_js = tmp_path / "plotly-shared-patched.min.js"
    shared_js.write_text("patched", encoding="utf-8")
    monkeypatch.setattr(chart_renderer, "ensure_patched_plotly_js", lambda: str(shared_js))

    page = SimpleNamespace()
    renderer = chart_renderer.ChartRenderer(page)
    view = FakeView()

    renderer._load_plotly_to_view(view, go.Figure(data=[go.Scatter(x=[1], y=[2])]))

    loaded_path = view.loaded_url.toLocalFile()
    assert loaded_path.endswith(".html")
    assert "plotly-shared-patched.min.js" in open(loaded_path, encoding="utf-8").read()
    assert Path(page._view_temp_files[view]) == Path(loaded_path)


def test_chart_renderer_main_fig_uses_date_and_decimal_hover_format():
    from types import SimpleNamespace
    from src.ui.pages.comparison.utils import chart_renderer

    df = pd.DataFrame(
        {"Portföy": [100.0, 104.307363]},
        index=pd.to_datetime(["2026-06-01", "2026-06-02"]),
    )
    renderer = chart_renderer.ChartRenderer(SimpleNamespace())

    fig = renderer._build_main_fig(df, "Normal", None, {})

    assert fig.layout.xaxis.tickformat == "%d.%m.%Y"
    assert "%{x|%d.%m.%Y}" in fig.data[0].hovertemplate
    assert "%{y:.2f}" in fig.data[0].hovertemplate


def test_chart_renderer_builds_contextual_download_filename():
    from types import SimpleNamespace
    from src.ui.pages.comparison.utils import chart_renderer
    from src.ui.pages.comparison.utils.chart_renderer import _DownloadCtx

    page = SimpleNamespace(
        ribbon_bar=SimpleNamespace(),
        _asset_labels={"dashboard": "Ana Portföy", "xu100": "BIST 100"},
    )
    renderer = chart_renderer.ChartRenderer(page)

    ctx = _DownloadCtx(
        selected_assets=["dashboard", "xu100"],
        ratio_assets=None,
        code_to_label={},
        asset_labels=page._asset_labels,
    )
    filename = renderer._build_download_filename(
        chart_key="main",
        mode="Normal",
        start_date=date(2026, 3, 8),
        end_date=date(2026, 6, 5),
        ctx=ctx,
    )

    assert filename == "ana_portfoy_bist_100_ana_performans_normal_08.03.2026_05.06.2026"


def test_chart_renderer_ratio_mode_uses_pay_and_payda_in_download_filename():
    from types import SimpleNamespace
    from src.ui.pages.comparison.utils import chart_renderer
    from src.ui.pages.comparison.utils.chart_renderer import _DownloadCtx
    from src.ui.shared.locale_tr import L10N

    page = SimpleNamespace(
        ribbon_bar=SimpleNamespace(),
        _asset_labels={"portfolio:4": "Portföy 4", "dashboard": "Ana Portföy"},
    )
    renderer = chart_renderer.ChartRenderer(page)

    ctx = _DownloadCtx(
        selected_assets=["dashboard", "portfolio:4", "xu100"],
        ratio_assets=("portfolio:4", "dashboard"),
        code_to_label={},
        asset_labels=page._asset_labels,
    )
    filename = renderer._build_download_filename(
        chart_key="main",
        mode=L10N.RASYO_MODU,
        start_date=date(2026, 3, 8),
        end_date=date(2026, 6, 5),
        ctx=ctx,
    )

    assert filename == "portfoy_4_ana_portfoy_ana_performans_rasyo_modu_08.03.2026_05.06.2026"


def test_chart_view_manager_creates_view_with_expanding_size_policy():
    page = ComparisonPage(MockContainer())
    view = page._view_manager.get_or_create_view("main")

    assert view is not None
    assert view.minimumHeight() == 350
    assert view.sizePolicy().horizontalPolicy() == QSizePolicy.Expanding
    assert view.sizePolicy().verticalPolicy() == QSizePolicy.Expanding


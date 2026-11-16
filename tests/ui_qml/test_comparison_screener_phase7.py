"""
Faz 7 Karşılaştırma Laboratuvarı & BIST Sinyal Tarayıcısı Doğrulama Testi.
"""
from __future__ import annotations

from pathlib import Path
import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineQuick import QtWebEngineQuick

from src.application.container import AppContainer
from src.ui_qml.controllers.shell_controller import ShellController
from src.ui_qml.controllers.chart_controller import ChartController
from src.ui_qml.controllers.dashboard_controller import DashboardController
from src.ui_qml.controllers.watchlist_controller import WatchlistController
from src.ui_qml.controllers.stock_360_controller import Stock360Controller
from src.ui_qml.controllers.model_portfolio_controller import ModelPortfolioController
from src.ui_qml.controllers.comparison_controller import ComparisonController
from src.ui_qml.controllers.screener_controller import ScreenerController


@pytest.fixture(scope="session")
def qapp():
    QtWebEngineQuick.initialize()
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def container():
    return AppContainer()


def test_comparison_controller_initialization(qapp, container):
    """ComparisonController'ın başlatılmasını ve varsayılan alanlarını test eder."""
    ctrl = ComparisonController(container=container)
    assert isinstance(ctrl.assetOptions, list)
    assert isinstance(ctrl.selectedAssets, list)
    assert ctrl.chartHtml == ""
    assert isinstance(ctrl.metricsList, list)
    assert not ctrl.isLoading
    assert ctrl.periodLabel == "3A"


def test_comparison_no_data_flag_distinguishes_empty_result_from_empty_selection(qapp, container):
    """D-01: seçim varken veri yoksa `noData` açılır (arayüz 'veri bulunamadı' der); yeni hesaplama ve sonuçla kapanır."""
    import pandas as pd

    ctrl = ComparisonController(container=container)
    assert not ctrl.noData
    seen = []
    ctrl.noDataChanged.connect(lambda: seen.append(ctrl.noData))

    ctrl._apply_empty_result()
    assert ctrl.noData and ctrl.chartHtml == ""

    aligned = pd.DataFrame({"A": [100.0, 101.0]}, index=pd.to_datetime(["2026-01-01", "2026-01-02"]))
    ctrl._apply_calculation_result(aligned, {"A": "A"}, [])
    assert not ctrl.noData
    assert seen == [True, False]


def test_comparison_controller_assets_and_run(qapp, container):
    """Varlık listesi yükleme, seçim ve karşılaştırma hesaplamasını test eder."""
    ctrl = ComparisonController(container=container)
    ctrl.loadAssetOptions()

    assert len(ctrl.assetOptions) > 0
    first = ctrl.assetOptions[0]
    assert "code" in first
    assert "label" in first

    # Varlık seçimi
    ctrl.toggleAsset(first["code"], True)
    assert first["code"] in ctrl.selectedAssets

    # Karşılaştırmayı doğrudan çalıştır
    ctrl._worker_calculate(ctrl._selected_codes, *ctrl._resolve_range())
    assert isinstance(ctrl.metricsList, list)

    # Modlar ve sekmeler testi
    ctrl.setComparisonMode("NORMAL")
    assert ctrl.comparisonMode == "NORMAL"
    ctrl.setComparisonMode("RATIO")
    assert ctrl.comparisonMode == "RATIO"
    ctrl.setActiveChartTab(1)  # Drawdown
    assert ctrl.activeChartTab == 1
    ctrl.setActiveChartTab(2)  # Periodic
    assert ctrl.activeChartTab == 2
    ctrl.setActiveChartTab(3)  # Scatter
    assert ctrl.activeChartTab == 3
    ctrl.setActiveChartTab(4)  # Treemap
    assert ctrl.activeChartTab == 4


def test_comparison_treemap_and_holdings_mode(qapp, container):
    """Treemap sekmesi, model portföy seçimi ve ana portföy ile varlık modlarını test eder."""
    ctrl = ComparisonController(container=container)
    assert ctrl.treemapMode == "HOLDINGS"
    assert ctrl.treemapPortfolio == "dashboard"

    # Portföy seçeneklerini yükleme
    ctrl.loadAssetOptions()
    assert len(ctrl.treemapPortfolioOptions) >= 1
    codes = [p["code"] for p in ctrl.treemapPortfolioOptions]
    assert "dashboard" in codes

    # Mod değişimi
    ctrl.setTreemapMode("ASSETS")
    assert ctrl.treemapMode == "ASSETS"
    ctrl.setTreemapMode("HOLDINGS")
    assert ctrl.treemapMode == "HOLDINGS"

    # Model portföy değiştirme testi
    model_opts = [c for c in codes if c != "dashboard"]
    if model_opts:
        target_model = model_opts[0]
        ctrl.setTreemapPortfolio(target_model)
        assert ctrl.treemapPortfolio == target_model
        holdings_model = ctrl._get_portfolio_holdings(target_model)
        assert isinstance(holdings_model, list)

    # Ana portföy hisselerini çekme testi
    ctrl.setTreemapPortfolio("dashboard")
    holdings = ctrl._get_portfolio_holdings()
    assert isinstance(holdings, list)
    if holdings:
        first = holdings[0]
        assert "code" in first
        assert "label" in first
        assert "weight" in first
        assert "ret" in first
        assert "marketValue" in first
        assert "costValue" in first

    # Treemap HTML üretim testi
    html = ctrl._build_treemap_html()
    assert "treemap-container" in html
    assert "tooltip" in html



def test_screener_controller_initialization_and_filters(qapp, container, wait_until):
    """ScreenerController ve hazır filtre tanımlarını test eder."""
    ctrl = ScreenerController(container=container)
    assert len(ctrl.filterOptions) >= 3
    # İlk seçenek "Tüm Stratejiler" olmalı
    assert ctrl.filterOptions[0]["key"] == ""
    assert not ctrl.isRunning
    assert ctrl._selected_filter == ""

    # Filtre değiştirme
    ctrl.setFilter(ctrl.filterOptions[1]["key"])
    assert ctrl._selected_filter == ctrl.filterOptions[1]["key"]

    # Asenkron tarama ve sinyal testi (Mock servis ile)
    from unittest.mock import MagicMock
    from src.application.services.analysis.technical.screener_service import ScreenerMatch

    mock_service = MagicMock()
    mock_service.scan.return_value = [
        ScreenerMatch(ticker="THYAO", filter_key="rsi_oversold", filter_label="Aşırı Satım", close_price=300.0)
    ]
    ctrl._screener_service = mock_service
    ctrl.runScan()
    assert wait_until(lambda: not ctrl.isRunning), "Tarama tamamlanmadı"
    assert not ctrl.isRunning
    assert len(ctrl.matchesList) == 1
    assert ctrl.matchesList[0]["ticker"] == "THYAO"
    assert "300,00 ₺" in ctrl.matchesList[0]["closePrice"]


def test_comparison_qml_view_compilation(qapp, container):
    """ComparisonView.qml dosyasının QML motorunda hatasız derlendiğini test eder."""
    engine = QQmlApplicationEngine()

    shell_ctrl = ShellController(container=container, parent=engine)
    chart_ctrl = ChartController(container=container, parent=engine)
    dash_ctrl = DashboardController(container=container, parent=engine)
    watchlist_ctrl = WatchlistController(container=container, parent=engine)
    stock_360_ctrl = Stock360Controller(container=container, parent=engine)
    portfolio_ctrl = ModelPortfolioController(container=container, parent=engine)
    comparison_ctrl = ComparisonController(container=container, parent=engine)
    screener_ctrl = ScreenerController(container=container, parent=engine)

    ctx = engine.rootContext()
    ctx.setContextProperty("shellController", shell_ctrl)
    ctx.setContextProperty("chartController", chart_ctrl)
    ctx.setContextProperty("dashboardController", dash_ctrl)
    ctx.setContextProperty("watchlistController", watchlist_ctrl)
    ctx.setContextProperty("stock360Controller", stock_360_ctrl)
    ctx.setContextProperty("portfolioController", portfolio_ctrl)
    ctx.setContextProperty("comparisonController", comparison_ctrl)
    ctx.setContextProperty("screenerController", screener_ctrl)

    qml_dir = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"
    engine.addImportPath(str(qml_dir))

    view_file = qml_dir / "views" / "ComparisonView.qml"
    assert view_file.exists(), f"{view_file} bulunamadı!"

    component = QQmlComponent(engine, QUrl.fromLocalFile(str(view_file)))
    if not component.isReady():
        errors = [err.toString() for err in component.errors()]
        pytest.fail(f"ComparisonView.qml derlenemedi:\n" + "\n".join(errors))

    item = component.create()
    assert item is not None, "ComparisonView item nesnesi oluşturulamadı!"


def test_screener_qml_view_compilation(qapp, container):
    """ScreenerView.qml dosyasının QML motorunda hatasız derlendiğini test eder."""
    engine = QQmlApplicationEngine()

    shell_ctrl = ShellController(container=container, parent=engine)
    chart_ctrl = ChartController(container=container, parent=engine)
    dash_ctrl = DashboardController(container=container, parent=engine)
    watchlist_ctrl = WatchlistController(container=container, parent=engine)
    stock_360_ctrl = Stock360Controller(container=container, parent=engine)
    portfolio_ctrl = ModelPortfolioController(container=container, parent=engine)
    comparison_ctrl = ComparisonController(container=container, parent=engine)
    screener_ctrl = ScreenerController(container=container, parent=engine)

    ctx = engine.rootContext()
    ctx.setContextProperty("shellController", shell_ctrl)
    ctx.setContextProperty("chartController", chart_ctrl)
    ctx.setContextProperty("dashboardController", dash_ctrl)
    ctx.setContextProperty("watchlistController", watchlist_ctrl)
    ctx.setContextProperty("stock360Controller", stock_360_ctrl)
    ctx.setContextProperty("portfolioController", portfolio_ctrl)
    ctx.setContextProperty("comparisonController", comparison_ctrl)
    ctx.setContextProperty("screenerController", screener_ctrl)

    qml_dir = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"
    engine.addImportPath(str(qml_dir))

    view_file = qml_dir / "views" / "ScreenerView.qml"
    assert view_file.exists(), f"{view_file} bulunamadı!"

    component = QQmlComponent(engine, QUrl.fromLocalFile(str(view_file)))
    if not component.isReady():
        errors = [err.toString() for err in component.errors()]
        pytest.fail(f"ScreenerView.qml derlenemedi:\n" + "\n".join(errors))

    item = component.create()
    assert item is not None, "ScreenerView item nesnesi oluşturulamadı!"


def _find_text_item(root_obj, target_text: str):
    from PySide6.QtQuick import QQuickItem

    queue = [root_obj]
    while queue:
        obj = queue.pop(0)
        if isinstance(obj, QQuickItem) and obj.isVisible() and obj.property("text") == target_text:
            return obj
        queue.extend(obj.childItems() if isinstance(obj, QQuickItem) else [])
    return None


def _make_fake_click_screener(parent):
    from PySide6.QtCore import QObject, Property, Signal, Slot

    class FakeScreener(QObject):
        filterOptionsChanged = Signal()
        matchesChanged = Signal()
        isRunningChanged = Signal()
        statusTextChanged = Signal()

        def __init__(self, obj_parent=None):
            super().__init__(obj_parent)
            self._matches = [
                {
                    "ticker": "BALAT.IS",
                    "filterLabel": "MACD Kesişim + Hacim Patlaması",
                    "closePrice": "56,25 ₺",
                    "closePriceRaw": 56.25,
                }
            ]

        @Property(list, notify=filterOptionsChanged)
        def filterOptions(self):
            return [{"key": "", "label": "Tüm Stratejiler"}]

        @Property(list, notify=matchesChanged)
        def matchesList(self):
            return self._matches

        @Property(bool, notify=isRunningChanged)
        def isRunning(self):
            return False

        @Property(str, notify=statusTextChanged)
        def statusText(self):
            return "Tarama tamamlandı: 1 hisse sinyal verdi"

        @Slot(str)
        def setFilter(self, _key):
            pass

        @Slot()
        def runScan(self):
            pass

    return FakeScreener(parent)


def _make_screener_click_fakes(parent):
    from PySide6.QtCore import QObject, Slot

    class _RecorderCtrl(QObject):
        def __init__(self, obj_parent=None):
            super().__init__(obj_parent)
            self.calls = []

    class FakeChart(_RecorderCtrl):
        @Slot(str)
        def loadTicker(self, ticker):
            self.calls.append(ticker)

    class FakeStock360(_RecorderCtrl):
        @Slot(str)
        def searchTicker(self, ticker):
            self.calls.append(ticker)

    class FakeShell(_RecorderCtrl):
        @Slot(int)
        def navigateTo(self, page):
            self.calls.append(page)

    chart_ctrl = FakeChart(parent)
    chart_ctrl.loaded = chart_ctrl.calls
    stock360_ctrl = FakeStock360(parent)
    stock360_ctrl.searched = stock360_ctrl.calls
    shell_ctrl = FakeShell(parent)
    shell_ctrl.pages = shell_ctrl.calls
    return _make_fake_click_screener(parent), chart_ctrl, stock360_ctrl, shell_ctrl


def _mount_screener_for_clicks(qapp):
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtQuick import QQuickWindow

    engine = QQmlApplicationEngine()
    screener_ctrl, chart_ctrl, stock360_ctrl, shell_ctrl = _make_screener_click_fakes(engine)

    ctx = engine.rootContext()
    ctx.setContextProperty("screenerController", screener_ctrl)
    ctx.setContextProperty("chartController", chart_ctrl)
    ctx.setContextProperty("stock360Controller", stock360_ctrl)
    ctx.setContextProperty("shellController", shell_ctrl)

    qml_dir = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"
    engine.addImportPath(str(qml_dir))
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml_dir / "views" / "ScreenerView.qml")))
    assert component.isReady(), "; ".join(e.toString() for e in component.errors())

    window = QQuickWindow()
    window.resize(1000, 600)
    item = component.create()
    assert item is not None
    item.setParentItem(window.contentItem())
    item.setWidth(1000)
    item.setHeight(600)
    window.show()
    for _ in range(12):
        QCoreApplication.processEvents()

    return window, item, chart_ctrl, stock360_ctrl, shell_ctrl, engine, component


def test_screener_chart_button_opens_chart_not_stock360(qapp, wait_until):
    """Grafik butonuna tek tıklama doğrudan Grafik sayfasını (0) açar; Hisse 360'a (3) gitmez."""
    from PySide6.QtCore import QCoreApplication, QPointF, Qt
    from PySide6.QtTest import QTest

    window, item, chart_ctrl, stock360_ctrl, shell_ctrl, engine, component = _mount_screener_for_clicks(qapp)
    try:
        chart_label = _find_text_item(item, "Grafik")
        assert chart_label is not None, "Grafik butonu metni bulunamadı"
        pt = chart_label.mapToScene(QPointF(chart_label.width() / 2, chart_label.height() / 2)).toPoint()
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, pt)
        assert wait_until(lambda: shell_ctrl.pages == [0], timeout=1.0), (
            f"Grafik butonu Grafik (0) yerine {shell_ctrl.pages} sayfasına gitti"
        )
        # Tek tık timer'ı tetiklenmeyeceğinden emin olmak için bekle
        QTest.qWait(300)
        QCoreApplication.processEvents()
        assert chart_ctrl.loaded == ["BALAT"]
        assert stock360_ctrl.searched == []
        assert shell_ctrl.pages == [0]
    finally:
        window.close()
        item.deleteLater()
        engine.deleteLater()


def test_screener_row_double_click_opens_chart_without_opening_stock360(qapp, wait_until):
    """Sonuç satırına çift tıklama Hisse 360'a gitmeden doğrudan Grafik sayfasını (0) açar."""
    from PySide6.QtCore import QCoreApplication, QPointF, Qt
    from PySide6.QtTest import QTest

    window, item, chart_ctrl, stock360_ctrl, shell_ctrl, engine, component = _mount_screener_for_clicks(qapp)
    try:
        ticker_label = _find_text_item(item, "BALAT.IS")
        assert ticker_label is not None, "Satır sembolü bulunamadı"
        pt = ticker_label.mapToScene(QPointF(ticker_label.width() / 2, ticker_label.height() / 2)).toPoint()
        QTest.mouseDClick(window, Qt.LeftButton, Qt.NoModifier, pt)
        assert wait_until(lambda: shell_ctrl.pages == [0], timeout=1.0), (
            f"Çift tıklama Grafik (0) yerine {shell_ctrl.pages} sayfasına gitti"
        )
        QTest.qWait(300)
        QCoreApplication.processEvents()
        assert chart_ctrl.loaded == ["BALAT"]
        assert stock360_ctrl.searched == []
        assert shell_ctrl.pages == [0]
    finally:
        window.close()
        item.deleteLater()
        engine.deleteLater()


def test_screener_row_single_click_opens_stock360(qapp, wait_until):
    """Sonuç satırına tek tıklama kısa gecikme sonrası Hisse 360 (3) sayfasını açar."""
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtTest import QTest

    window, item, chart_ctrl, stock360_ctrl, shell_ctrl, engine, component = _mount_screener_for_clicks(qapp)
    try:
        ticker_label = _find_text_item(item, "BALAT.IS")
        assert ticker_label is not None, "Satır sembolü bulunamadı"
        pt = ticker_label.mapToScene(QPointF(ticker_label.width() / 2, ticker_label.height() / 2)).toPoint()
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, pt)
        assert wait_until(lambda: shell_ctrl.pages == [3], timeout=1.5), (
            f"Tek tıklama Hisse 360 (3) açmadı: {shell_ctrl.pages}"
        )
        assert stock360_ctrl.searched == ["BALAT"]
        assert chart_ctrl.loaded == ["BALAT"]
    finally:
        window.close()
        item.deleteLater()
        engine.deleteLater()

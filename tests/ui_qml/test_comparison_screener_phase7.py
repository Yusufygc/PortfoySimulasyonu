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
    ctrl._worker_calculate(ctrl._selected_codes, ctrl._period_label)
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
    """Treemap sekmesi ve ana portföy hisseleri (HOLDINGS) ile varlık (ASSETS) modlarını test eder."""
    ctrl = ComparisonController(container=container)
    assert ctrl.treemapMode == "HOLDINGS"

    # Mod değişimi
    ctrl.setTreemapMode("ASSETS")
    assert ctrl.treemapMode == "ASSETS"
    ctrl.setTreemapMode("HOLDINGS")
    assert ctrl.treemapMode == "HOLDINGS"

    # Portföy hisselerini çekme testi
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



def test_screener_controller_initialization_and_filters(qapp, container):
    """ScreenerController ve hazır filtre tanımlarını test eder."""
    ctrl = ScreenerController(container=container)
    assert len(ctrl.filterOptions) >= 3
    # İlk seçenek "Tüm Stratejiler" olmalı
    assert ctrl.filterOptions[0]["key"] == ""
    assert not ctrl.isRunning
    assert ctrl.selectedFilter == ""

    # Filtre değiştirme
    ctrl.setFilter(ctrl.filterOptions[1]["key"])
    assert ctrl.selectedFilter == ctrl.filterOptions[1]["key"]


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

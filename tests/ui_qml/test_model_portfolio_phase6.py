"""
Faz 6 Model Portföyler Doğrulama Testi — Sanal portföy simülasyonu, nakit akışı,
alım/satım işlemleri, KPI özetleri ve QML entegrasyonu.
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


def test_model_portfolio_controller_initialization(qapp, container):
    """Controller'ın sağlıklı ilklendirildiğini ve varsayılan alanlarını doğrular."""
    ctrl = ModelPortfolioController(container=container)
    assert ctrl.currentPortfolioId == -1
    assert ctrl.currentPortfolioName == ""
    assert isinstance(ctrl.portfolioList, list)
    assert isinstance(ctrl.summaryNetCapital, str)
    assert isinstance(ctrl.summaryRemainingCash, str)
    assert isinstance(ctrl.summaryTotalValue, str)
    assert isinstance(ctrl.summaryProfitLoss, str)
    assert isinstance(ctrl.summaryProfitLossPct, float)
    assert ctrl.summaryProfitLossState in ["positive", "negative", "neutral"]
    assert isinstance(ctrl.positionsList, list)
    assert isinstance(ctrl.hasPositions, bool)
    assert not ctrl.isLoading


def test_model_portfolio_refresh_data(qapp, container):
    """refreshData çağrısıyla veritabanındaki portföylerin yüklendiğini doğrular."""
    ctrl = ModelPortfolioController(container=container)
    ctrl.refreshData()

    # DB'de kayıtlı portföy varsa listeye dolmalı ve ilki seçilmeli
    assert isinstance(ctrl.portfolioList, list)
    if len(ctrl.portfolioList) > 0:
        first = ctrl.portfolioList[0]
        assert "portfolioId" in first
        assert "name" in first
        assert "positionCount" in first
        assert ctrl.currentPortfolioId > 0
        assert ctrl.currentPortfolioName != ""


def test_model_portfolio_crud_lifecycle(qapp, container):
    """Portföy oluşturma, güncelleme ve silme döngüsünü test eder."""
    ctrl = ModelPortfolioController(container=container)
    test_name = "TEST_PORT_FZ6"
    test_desc = "Faz 6 Otomasyon Portföyü"

    # 1. Oluştur
    ctrl.createPortfolio(test_name, test_desc, 250000.0)
    created = next((p for p in ctrl.portfolioList if p["name"] == test_name), None)
    assert created is not None
    port_id = created["portfolioId"]

    # 2. Güncelle
    updated_name = "TEST_PORT_FZ6_UPD"
    ctrl.updatePortfolio(port_id, updated_name, "Güncellenmiş Açıklama")
    ctrl.refreshData()
    updated = next((p for p in ctrl.portfolioList if p["portfolioId"] == port_id), None)
    assert updated is not None
    assert updated["name"] == updated_name

    # 3. Sil
    ctrl.deletePortfolio(port_id)
    ctrl.refreshData()
    deleted = next((p for p in ctrl.portfolioList if p["portfolioId"] == port_id), None)
    assert deleted is None


def test_model_portfolio_qml_view_compilation(qapp, container):
    """ModelPortfolioView.qml dosyasının QML motorunda hatasız parse ve import edildiğini test eder."""
    engine = QQmlApplicationEngine()

    shell_ctrl = ShellController(container=container, parent=engine)
    chart_ctrl = ChartController(container=container, parent=engine)
    dash_ctrl = DashboardController(container=container, parent=engine)
    watchlist_ctrl = WatchlistController(container=container, parent=engine)
    stock_360_ctrl = Stock360Controller(container=container, parent=engine)
    portfolio_ctrl = ModelPortfolioController(container=container, parent=engine)

    ctx = engine.rootContext()
    ctx.setContextProperty("shellController", shell_ctrl)
    ctx.setContextProperty("chartController", chart_ctrl)
    ctx.setContextProperty("dashboardController", dash_ctrl)
    ctx.setContextProperty("watchlistController", watchlist_ctrl)
    ctx.setContextProperty("stock360Controller", stock_360_ctrl)
    ctx.setContextProperty("portfolioController", portfolio_ctrl)

    qml_dir = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"
    engine.addImportPath(str(qml_dir))

    view_file = qml_dir / "views" / "ModelPortfolioView.qml"
    assert view_file.exists(), f"{view_file} bulunamadı!"

    component = QQmlComponent(engine, QUrl.fromLocalFile(str(view_file)))
    if not component.isReady():
        errors = [err.toString() for err in component.errors()]
        pytest.fail(f"ModelPortfolioView.qml derlenemedi:\n" + "\n".join(errors))

    item = component.create()
    assert item is not None, "ModelPortfolioView item nesnesi oluşturulamadı!"

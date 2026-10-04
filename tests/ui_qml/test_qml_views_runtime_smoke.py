"""Büyük QML görünümleri için çalışma zamanı duman testi.

Her görünüm uygulamadakiyle aynı bağlam özellikleriyle (denetleyiciler) oluşturulur, tüm sekme/mod değerleri sırayla
etkinleştirilir ve QML motorunun hiçbir uyarı (tanımsız kimlik, bağlama hatası, TypeError) üretmediği doğrulanır.
Bölme/yeniden düzenleme sırasında koparılan bağlamaları (`root.*`, üst kimlik başvuruları) yakalamak içindir.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtWebEngineQuick import QtWebEngineQuick
from PySide6.QtWidgets import QApplication

from src.application.container import AppContainer
from src.ui_qml.controllers.ai_advisor_controller import AiAdvisorController
from src.ui_qml.controllers.chart_controller import ChartController
from src.ui_qml.controllers.comparison_controller import ComparisonController
from src.ui_qml.controllers.corporate_action_controller import CorporateActionController
from src.ui_qml.controllers.dashboard_controller import DashboardController
from src.ui_qml.controllers.dividend_controller import DividendController
from src.ui_qml.controllers.golden_cross_controller import GoldenCrossController
from src.ui_qml.controllers.market_adjustment_controller import MarketAdjustmentController
from src.ui_qml.controllers.market_sync_controller import MarketSyncController
from src.ui_qml.controllers.market_ticker_controller import MarketTickerController
from src.ui_qml.controllers.model_analysis_controller import ModelAnalysisController
from src.ui_qml.controllers.model_portfolio_controller import ModelPortfolioController
from src.ui_qml.controllers.optimization_controller import OptimizationController
from src.ui_qml.controllers.planning_controller import PlanningController
from src.ui_qml.controllers.price_data_controller import PriceDataController
from src.ui_qml.controllers.risk_profile_controller import RiskProfileController
from src.ui_qml.controllers.screener_controller import ScreenerController
from src.ui_qml.controllers.settings_controller import SettingsController
from src.ui_qml.controllers.shell_controller import ShellController
from src.ui_qml.controllers.startup_jobs_controller import StartupJobsController
from src.ui_qml.controllers.stock_360_controller import Stock360Controller
from src.ui_qml.controllers.stock_detail_controller import StockDetailController
from src.ui_qml.controllers.strategy_backtest_controller import StrategyBacktestController
from src.ui_qml.controllers.system_controller import SystemController
from src.ui_qml.controllers.watchlist_controller import WatchlistController

QML_DIR = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml"

# (qml dosyası, değiştirilen özellik, değerler, denetleyici üzerinden sürücü (ad, yuva, değerler) ya da None)
TARGETS = {
    "SettingsView": ("views/SettingsView.qml", "activeTabIndex", range(8), None),
    "AiAdvisorView": ("views/AiAdvisorView.qml", "mode", range(2), None),
    "OptimizationView": ("views/OptimizationView.qml", None, [None], None),
    # Hisse 360 görünüm modları (0 Genel Bakış, 1 Finansal, 2 KAP) bir denetleyici yuvasıyla değişir
    "Stock360View": ("views/Stock360View.qml", None, [None], ("stock360Controller", "setViewMode", (0, 1, 2, 0))),
    # Alt sekme durumu StockDetailTabsPanel bileşeninde: çocuk bileşenin özelliği değiştirilir
    "StockDetailModal": ("components/StockDetailModal.qml", None, [None], ("child", "StockDetailTabsPanel", "activeTab", (0, 1, 0))),
}


@pytest.fixture(scope="session")
def qapp():
    QtWebEngineQuick.initialize()
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def qml_env(qapp):
    container = AppContainer()
    engine = QQmlApplicationEngine()
    controllers = {
        "shellController": ShellController(container=container, parent=engine),
        "chartController": ChartController(container=container, parent=engine),
        "dashboardController": DashboardController(container=container, parent=engine),
        "watchlistController": WatchlistController(container=container, parent=engine),
        "stock360Controller": Stock360Controller(container=container, parent=engine),
        "portfolioController": ModelPortfolioController(container=container, parent=engine),
        "comparisonController": ComparisonController(container=container, parent=engine),
        "screenerController": ScreenerController(container=container, parent=engine),
        "planningController": PlanningController(container=container, parent=engine),
        "strategyBacktestController": StrategyBacktestController(container=container, parent=engine),
        "marketSyncController": MarketSyncController(parent=engine, container=container),
        "optimizationController": OptimizationController(container=container, parent=engine),
        "aiAdvisorController": AiAdvisorController(container=container, parent=engine),
        "settingsController": SettingsController(container=container, parent=engine),
        "stockDetailController": StockDetailController(container=container, parent=engine),
        "corporateActionController": CorporateActionController(container=container, parent=engine),
        "dividendController": DividendController(container=container, parent=engine),
        "priceDataController": PriceDataController(container=container, parent=engine),
        "startupJobsController": StartupJobsController(container=container, parent=engine),
        "goldenCrossController": GoldenCrossController(container=container, parent=engine),
        "riskProfileController": RiskProfileController(container=container, parent=engine),
        "marketAdjustmentController": MarketAdjustmentController(container=container, parent=engine),
        "systemController": SystemController(container=container, parent=engine),
        "marketTickerController": MarketTickerController(container=container, parent=engine),
        "modelAnalysisController": ModelAnalysisController(container=container, parent=engine),
    }
    context = engine.rootContext()
    for name, controller in controllers.items():
        context.setContextProperty(name, controller)
    engine.addImportPath(str(QML_DIR))
    warnings: list[str] = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    yield engine, warnings, controllers
    engine.deleteLater()


def _pump(times: int = 6) -> None:
    for _ in range(times):
        QCoreApplication.processEvents()


@pytest.mark.parametrize("name", sorted(TARGETS))
def test_view_loads_every_tab_without_qml_warnings(qml_env, name):
    engine, warnings, controllers = qml_env
    relative_path, property_name, values, driver = TARGETS[name]
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / relative_path)))
    assert component.isReady(), "; ".join(e.toString() for e in component.errors())

    item = component.create()
    assert item is not None, f"{name} oluşturulamadı"
    item.setProperty("width", 1280)
    item.setProperty("height", 820)
    _pump()
    for value in values:
        if property_name is not None:
            item.setProperty(property_name, value)
        _pump()

    if driver is not None and driver[0] == "child":
        _, class_name, property_name, driver_values = driver
        children = [o for o in item.findChildren(QObject) if class_name in o.metaObject().className()]
        assert children, f"{class_name} bulunamadı"
        for value in driver_values:
            assert children[0].setProperty(property_name, value), f"{class_name}.{property_name} ayarlanamadı"
            _pump(10)
    elif driver is not None:
        controller_name, slot_name, driver_values = driver
        for value in driver_values:
            getattr(controllers[controller_name], slot_name)(value)
            _pump(10)

    assert warnings == [], "\n".join(warnings)

"""
QML Uygulama Giriş Noktası — PySide6, QtQuick ve WebEngine tabanlı modern UI çalıştırıcısı.
"""
from __future__ import annotations

import os
import sys
import logging
from pathlib import Path

from PySide6.QtCore import QUrl, QCoreApplication
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWebEngineQuick import QtWebEngineQuick
from PySide6.QtQuickControls2 import QQuickStyle

from src.ui_qml.controllers.shell_controller import ShellController
from src.ui_qml.controllers.chart_controller import ChartController
from src.ui_qml.controllers.dashboard_controller import DashboardController
from src.ui_qml.controllers.watchlist_controller import WatchlistController
from src.ui_qml.controllers.stock_360_controller import Stock360Controller
from src.ui_qml.controllers.model_portfolio_controller import ModelPortfolioController
from src.ui_qml.controllers.comparison_controller import ComparisonController
from src.ui_qml.controllers.screener_controller import ScreenerController
from src.ui_qml.controllers.planning_controller import PlanningController
from src.ui_qml.controllers.market_sync_controller import MarketSyncController
from src.ui_qml.controllers.optimization_controller import OptimizationController
from src.ui_qml.controllers.ai_advisor_controller import AiAdvisorController
from src.ui_qml.controllers.settings_controller import SettingsController
from src.ui_qml.controllers.stock_detail_controller import StockDetailController
from src.ui_qml.controllers.corporate_action_controller import CorporateActionController
from src.ui_qml.controllers.price_data_controller import PriceDataController
from src.ui_qml.controllers.startup_jobs_controller import StartupJobsController

logger = logging.getLogger(__name__)


def run_qml_app(container=None) -> int:
    """QML tabanlı modern arayüzü başlatır."""
    # Modern özel bileşenlerin ve kaydırma çubuklarının (ScrollBar) native stil tarafından ezilmemesi için Basic stil ayarlanır
    QQuickStyle.setStyle("Basic")

    # WebEngineQuick başlatması (QApplication öncesi veya hemen başında çağrılmalıdır)
    QtWebEngineQuick.initialize()

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setApplicationName("PortfoySimulasyonu")
    app.setOrganizationName("PortfoySim")

    engine = QQmlApplicationEngine()

    # DI Container
    if container is None:
        try:
            from src.application.container import AppContainer
            container = AppContainer()
        except Exception as exc:
            logger.warning("Container başlatılamadı, mock/offline modda devam ediliyor: %s", exc)

    # Controller'ları (ViewModels) ilklendir
    shell_ctrl = ShellController(container=container, parent=engine)
    chart_ctrl = ChartController(container=container, parent=engine)
    dash_ctrl = DashboardController(container=container, parent=engine)
    watchlist_ctrl = WatchlistController(container=container, parent=engine)
    stock_360_ctrl = Stock360Controller(container=container, parent=engine)
    portfolio_ctrl = ModelPortfolioController(container=container, parent=engine)
    comparison_ctrl = ComparisonController(container=container, parent=engine)
    screener_ctrl = ScreenerController(container=container, parent=engine)
    planning_ctrl = PlanningController(container=container, parent=engine)
    market_sync_ctrl = MarketSyncController(parent=engine, container=container)
    optimization_ctrl = OptimizationController(container=container, parent=engine)
    ai_advisor_ctrl = AiAdvisorController(container=container, parent=engine)
    settings_ctrl = SettingsController(container=container, parent=engine)
    stock_detail_ctrl = StockDetailController(container=container, parent=engine)
    corporate_action_ctrl = CorporateActionController(container=container, parent=engine)
    price_data_ctrl = PriceDataController(container=container, parent=engine)
    startup_jobs_ctrl = StartupJobsController(container=container, parent=engine)

    # Piyasa verisi senkronu yeni bar yazınca fiyata bağlı ekranları yenile
    market_sync_ctrl.dataSynced.connect(dash_ctrl.refreshMetrics)
    market_sync_ctrl.dataSynced.connect(portfolio_ctrl.refreshData)
    # Sermaye artırımı / fiyat güncellemesi / açılış backfill'i sonrası ekranları DB'den yeniden yükle
    for source in (corporate_action_ctrl.portfolioChanged, price_data_ctrl.pricesUpdated, startup_jobs_ctrl.pricesUpdated):
        source.connect(dash_ctrl.reloadPortfolio)
        source.connect(portfolio_ctrl.refreshData)

    # QML Context Property olarak bağla
    context = engine.rootContext()
    context.setContextProperty("shellController", shell_ctrl)
    context.setContextProperty("chartController", chart_ctrl)
    context.setContextProperty("dashboardController", dash_ctrl)
    context.setContextProperty("watchlistController", watchlist_ctrl)
    context.setContextProperty("stock360Controller", stock_360_ctrl)
    context.setContextProperty("portfolioController", portfolio_ctrl)
    context.setContextProperty("comparisonController", comparison_ctrl)
    context.setContextProperty("screenerController", screener_ctrl)
    context.setContextProperty("planningController", planning_ctrl)
    context.setContextProperty("marketSyncController", market_sync_ctrl)
    context.setContextProperty("optimizationController", optimization_ctrl)
    context.setContextProperty("aiAdvisorController", ai_advisor_ctrl)
    context.setContextProperty("settingsController", settings_ctrl)
    context.setContextProperty("stockDetailController", stock_detail_ctrl)
    context.setContextProperty("corporateActionController", corporate_action_ctrl)
    context.setContextProperty("priceDataController", price_data_ctrl)
    context.setContextProperty("startupJobsController", startup_jobs_ctrl)

    # QML import dizinleri
    qml_dir = Path(__file__).resolve().parent / "qml"
    engine.addImportPath(str(qml_dir))

    # Main.qml yükle
    main_qml = qml_dir / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(main_qml)))

    if not engine.rootObjects():
        logger.error("Main.qml yüklenemedi!")
        return -1

    # Ekran çözünürlüğüne göre pencereyi otomatik sınırla ve ekranda merkeze al
    primary_screen = app.primaryScreen()
    if primary_screen:
        geom = primary_screen.availableGeometry()
        win = engine.rootObjects()[0]
        cur_w = int(win.property("width") or 1200)
        cur_h = int(win.property("height") or 760)
        w = max(960, min(cur_w, geom.width() - 40))
        h = max(600, min(cur_h, geom.height() - 60))
        win.setProperty("width", w)
        win.setProperty("height", h)
        win.setProperty("x", geom.x() + max(0, (geom.width() - w) // 2))
        win.setProperty("y", geom.y() + max(0, (geom.height() - h) // 2))

    logger.info("QML Arayüzü başarıyla başlatıldı.")
    return app.exec()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(run_qml_app())

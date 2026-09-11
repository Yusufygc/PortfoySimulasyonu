"""
QML uygulama başlatıcısı (bkz. plan §7.1) — `QQmlApplicationEngine` kurulumu +
Container → Controller → rootContext köprüsü.

`Main.qml`, d3'te basit bir üst düğme ile `DashboardView`/`Stock360View`/
`ScreenerView`/`WatchlistView` arasında geçiş yapılabilen bir kabuktur; gerçek
sidebar + dinamik sayfa yükleyici (çok view arası geçiş) sonraki adımlarda bu
dosyanın üzerine inşa edilecek.

    python -m src.ui_qml.main
"""
from __future__ import annotations

import sys
from pathlib import Path

from src.qt_compat.qtgui import QGuiApplication
from src.qt_compat.qtqml import QQmlApplicationEngine, qmlRegisterType

from src.ui_qml.charts.bar_chart_item import BarChartItem
from src.ui_qml.charts.candlestick_chart_item import CandlestickChartItem
from src.ui_qml.charts.donut_chart_item import DonutChartItem
from src.ui_qml.charts.line_chart_item import LineChartItem
from src.ui_qml.charts.scatter_chart_item import ScatterChartItem
from src.ui_qml.charts.treemap_chart_item import TreemapChartItem
from src.ui_qml.controllers.ai_advisor_controller import AiAdvisorController
from src.ui_qml.controllers.analytics_controller import AnalyticsController
from src.ui_qml.controllers.cashflow_controller import CashflowController
from src.ui_qml.controllers.dashboard_controller import DashboardController
from src.ui_qml.controllers.optimization_controller import OptimizationController
from src.ui_qml.controllers.screener_controller import ScreenerController
from src.ui_qml.controllers.simulation_controller import SimulationController
from src.ui_qml.controllers.stock_360_controller import Stock360Controller
from src.ui_qml.controllers.watchlist_controller import WatchlistController

_QML_FILE = Path(__file__).parent / "qml" / "Main.qml"


def main() -> int:
    from src.application.container import AppContainer

    qmlRegisterType(LineChartItem, "PortfoyCharts", 1, 0, "LineChartItem")
    qmlRegisterType(DonutChartItem, "PortfoyCharts", 1, 0, "DonutChartItem")
    qmlRegisterType(CandlestickChartItem, "PortfoyCharts", 1, 0, "CandlestickChartItem")
    qmlRegisterType(BarChartItem, "PortfoyCharts", 1, 0, "BarChartItem")
    qmlRegisterType(ScatterChartItem, "PortfoyCharts", 1, 0, "ScatterChartItem")
    qmlRegisterType(TreemapChartItem, "PortfoyCharts", 1, 0, "TreemapChartItem")

    container = AppContainer()

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    dashboard_controller = DashboardController(container)
    engine.rootContext().setContextProperty("dashboardController", dashboard_controller)

    stock_360_controller = Stock360Controller(container)
    engine.rootContext().setContextProperty("stock360Controller", stock_360_controller)

    screener_controller = ScreenerController(container)
    engine.rootContext().setContextProperty("screenerController", screener_controller)

    watchlist_controller = WatchlistController(container)
    engine.rootContext().setContextProperty("watchlistController", watchlist_controller)

    analytics_controller = AnalyticsController(container)
    engine.rootContext().setContextProperty("analyticsController", analytics_controller)

    optimization_controller = OptimizationController(container)
    engine.rootContext().setContextProperty("optimizationController", optimization_controller)

    simulation_controller = SimulationController(container)
    engine.rootContext().setContextProperty("simulationController", simulation_controller)

    cashflow_controller = CashflowController(container)
    engine.rootContext().setContextProperty("cashflowController", cashflow_controller)

    ai_advisor_controller = AiAdvisorController(container)
    engine.rootContext().setContextProperty("aiAdvisorController", ai_advisor_controller)

    engine.load(str(_QML_FILE))
    root_objects = engine.rootObjects()
    if not root_objects:
        print("QML yüklenemedi:", _QML_FILE)
        return 1

    root_objects[0].setProperty("visible", True)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

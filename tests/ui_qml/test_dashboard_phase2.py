"""
Faz 2 Dashboard Doğrulama Testi — Pozisyon tablosu, Al/Sat emirleri, Sermaye yönetimi ve QML görünümü.
"""
from __future__ import annotations

from pathlib import Path
import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineQuick import QtWebEngineQuick

from src.ui_qml.controllers.shell_controller import ShellController
from src.ui_qml.controllers.chart_controller import ChartController
from src.ui_qml.controllers.dashboard_controller import DashboardController


@pytest.fixture(scope="session")
def qapp():
    QtWebEngineQuick.initialize()
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _container(cash="100000"):
    from decimal import Decimal
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    container = MagicMock()
    container.portfolio_service.get_cash_balance.return_value = Decimal(cash)
    container.portfolio_service.get_current_portfolio.return_value = SimpleNamespace(active_positions={1: object(), 2: object()})
    container.stock_lookup_service.get_stocks.return_value = {
        1: SimpleNamespace(ticker="THYAO.IS"), 2: SimpleNamespace(ticker="ASELS"),
    }
    return container


def test_dashboard_exposes_only_bist_operations_not_valuation(qapp):
    """Değerleme Portföyüm'dedir (UnifiedPortfolioService); bu denetleyici yalnızca BIST işlemlerini sunar."""
    controller = DashboardController(container=_container())

    assert controller.cashBalance == "₺100.000,00"
    assert controller.quickTickers[:2] == ["THYAO", "ASELS"]
    for removed in ("positionsModel", "totalValue", "allocationSlices", "dailyGainLoss", "holdingsCount"):
        assert not hasattr(controller, removed)


def test_dashboard_without_container_rejects_operations_instead_of_simulating(qapp):
    controller = DashboardController()
    events = []
    controller.tradeExecuted.connect(lambda ok, msg: events.append(ok))
    controller.capitalUpdated.connect(lambda ok, msg: events.append(ok))

    controller.submitTrade("THYAO", "BUY", 100, 250.0, "Test buy")
    controller.manageCapital("deposit", 25000.0, "Ek birikim")

    assert events == [False, False]
    assert controller.quickTickers == ["THYAO", "GARAN", "ASELS", "KCHOL"]


def test_dashboard_capital_management_goes_through_service(qapp):
    container = _container()
    controller = DashboardController(container=container)
    events = []
    controller.capitalUpdated.connect(lambda ok, msg: events.append(ok))

    controller.manageCapital("DEPOSIT", 25000.0, "Ek birikim")
    controller.manageCapital("WITHDRAW", 10000.0, "Nakit çekim")

    assert events == [True, True]
    container.cash_movement_service.add_deposit.assert_called_once()
    container.cash_movement_service.add_withdraw.assert_called_once()


def test_dashboard_qml_full_load(qapp):
    engine = QQmlApplicationEngine()

    shell_ctrl = ShellController(parent=engine)
    chart_ctrl = ChartController(parent=engine)
    dash_ctrl = DashboardController(parent=engine)

    engine.rootContext().setContextProperty("shellController", shell_ctrl)
    engine.rootContext().setContextProperty("chartController", chart_ctrl)
    engine.rootContext().setContextProperty("dashboardController", dash_ctrl)

    qml_dir = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"
    engine.addImportPath(str(qml_dir))

    warnings_list = []
    engine.warnings.connect(lambda warns: warnings_list.extend([w.toString() for w in warns]))

    main_qml = qml_dir / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(main_qml)))

    root_objects = engine.rootObjects()
    assert len(root_objects) > 0, f"Main.qml yüklenemedi! Hatalar: {warnings_list}"


def test_dashboard_with_real_container(qapp):
    import json
    from src.application.container import AppContainer

    container = AppContainer()
    dash_ctrl = DashboardController(container=container)
    chart_ctrl = ChartController(container=container)

    assert "₺" in dash_ctrl.cashBalance
    assert all(not t.endswith(".IS") for t in dash_ctrl.quickTickers)

    chart_data = []
    chart_ctrl.chartDataLoaded.connect(lambda t, p: chart_data.append((t, p)))
    chart_ctrl.loadTicker("OBAMS.IS")
    assert len(chart_data) == 1
    assert chart_data[0][0] == "OBAMS.IS"
    parsed = json.loads(chart_data[0][1])
    assert len(parsed["candles"]) > 0



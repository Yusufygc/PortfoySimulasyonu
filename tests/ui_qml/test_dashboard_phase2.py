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


def test_dashboard_kpis_and_positions_model(qapp):
    controller = DashboardController()

    # Model doğrulaması
    model = controller.positionsModel
    assert model.rowCount() == 8
    
    first_idx = model.index(0)
    ticker = model.data(first_idx, model.TickerRole)
    assert ticker == "THYAO"

    # KPI alanları
    assert "₺" in controller.totalValue
    assert "₺" in controller.cashBalance
    assert "%" in controller.cashRatio
    assert controller.holdingsCount == 8

    # Varlık Dağılımı Slices (Decimal/Float tip uyuşmazlığı kontrolü)
    slices = controller.allocationSlices
    assert isinstance(slices, list)
    assert len(slices) > 0
    for s in slices:
        assert "label" in s
        assert isinstance(s["pct"], float)
        assert "color" in s
        assert "amount" in s


def test_dashboard_trade_execution(qapp):
    controller = DashboardController()
    model = controller.positionsModel
    initial_cash = controller._capital

    events = []
    controller.tradeExecuted.connect(lambda s, msg: events.append((s, msg)))

    # 1. Başarılı Alım
    controller.submitTrade("THYAO", "BUY", 100, 250.0, "Test buy")
    assert len(events) == 1
    assert events[0][0] is True
    assert controller._capital == initial_cash - (100 * 250)

    # 2. Yetersiz Nakit Alım Hatası
    controller.submitTrade("THYAO", "BUY", 100000, 500.0, "Huge buy")
    assert len(events) == 2
    assert events[1][0] is False
    assert "Yetersiz nakit" in events[1][1]

    # 3. Başarılı Satış
    controller.submitTrade("THYAO", "SELL", 50, 260.0, "Test sell")
    assert len(events) == 3
    assert events[2][0] is True


def test_dashboard_capital_management(qapp):
    controller = DashboardController()
    initial_cash = controller._capital

    events = []
    controller.capitalUpdated.connect(lambda s, msg: events.append((s, msg)))

    # Yatırma
    controller.manageCapital("deposit", 25000.0, "Ek birikim")
    assert len(events) == 1
    assert events[0][0] is True
    assert controller._capital == initial_cash + 25000

    # Çekme
    controller.manageCapital("withdraw", 10000.0, "Nakit çekim")
    assert len(events) == 2
    assert events[1][0] is True
    assert controller._capital == initial_cash + 25000 - 10000


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

    assert dash_ctrl.holdingsCount == 7
    assert "₺" in dash_ctrl.totalValue

    chart_data = []
    chart_ctrl.chartDataLoaded.connect(lambda t, p: chart_data.append((t, p)))
    chart_ctrl.loadTicker("OBAMS.IS")
    assert len(chart_data) == 1
    assert chart_data[0][0] == "OBAMS.IS"
    parsed = json.loads(chart_data[0][1])
    assert len(parsed["candles"]) > 0

    real_slices = dash_ctrl.allocationSlices
    assert len(real_slices) >= 4
    assert any("PSGYO" in s["label"] for s in real_slices)


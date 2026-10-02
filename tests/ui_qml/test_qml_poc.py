"""
QML POC Doğrulama Testi — Main.qml ve Controller nesnelerinin hatasız yüklendiğini test eder.
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


def test_controllers_initialization(qapp):
    shell = ShellController()
    chart = ChartController()
    dash = DashboardController()

    assert shell.activePage == 0
    assert shell.pageTitle == "Ana Sayfa"
    assert chart.currentTicker == "THYAO"
    assert "₺" in dash.totalValue


def test_main_qml_syntax_and_load(qapp):
    engine = QQmlApplicationEngine()

    # Controller nesnelerini engine ebeveynliğiyle oluştur (GC engelleme)
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
    assert len(root_objects) > 0, f"Main.qml yüklenemedi! Uyarılar: {warnings_list}"

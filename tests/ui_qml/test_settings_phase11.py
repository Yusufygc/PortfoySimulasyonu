"""
test_settings_phase11.py — Faz 11 Uygulama Ayarları, Veritabanı Yönetimi & Dağıtım QML test paketi.

Kapsam:
- SettingsController ilklendirme ve varsayılan property değerleri
- Koyu / Açık tema geçişi (toggleTheme)
- API anahtarlarını kaydetme (saveApiKeys)
- SQLite ve DuckDB veritabanı istatistikleri (refreshDatabaseStats)
- Veritabanı bütünlük kontrolü (checkDatabaseIntegrity)
- Portföy Excel ve JSON dışa aktarımı
- SettingsView.qml dosyasının QML motorunda hatasız derlenmesi
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from src.application.container import AppContainer
from src.ui_qml.controllers.ai_advisor_controller import AiAdvisorController
from src.ui_qml.controllers.chart_controller import ChartController
from src.ui_qml.controllers.comparison_controller import ComparisonController
from src.ui_qml.controllers.dashboard_controller import DashboardController
from src.ui_qml.controllers.market_sync_controller import MarketSyncController
from src.ui_qml.controllers.model_portfolio_controller import ModelPortfolioController
from src.ui_qml.controllers.optimization_controller import OptimizationController
from src.ui_qml.controllers.planning_controller import PlanningController
from src.ui_qml.controllers.screener_controller import ScreenerController
from src.ui_qml.controllers.settings_controller import SettingsController
from src.ui_qml.controllers.shell_controller import ShellController
from src.ui_qml.controllers.stock_360_controller import Stock360Controller
from src.ui_qml.controllers.watchlist_controller import WatchlistController


@pytest.fixture
def container():
    return AppContainer()


def test_settings_controller_initialization():
    """SettingsController'ın varsayılan dosya yolları ve özelliklerini test eder."""
    ctrl = SettingsController(container=None)

    assert "portfolio.db" in ctrl.sqliteDbPath
    assert "market_history.duckdb" in ctrl.duckDbPath
    assert isinstance(ctrl.isDarkTheme, bool)
    assert ctrl.isSyncing is False
    assert isinstance(ctrl.isLoading, bool)


def test_settings_controller_toggle_theme():
    """toggleTheme slotunun temayı değiştirdiğini test eder."""
    ctrl = SettingsController(container=None)
    initial_theme = ctrl.isDarkTheme

    ctrl.toggleTheme()
    assert ctrl.isDarkTheme == (not initial_theme)

    ctrl.toggleTheme()
    assert ctrl.isDarkTheme == initial_theme


def test_settings_controller_save_api_keys():
    """saveApiKeys slotunun anahtarları başarıyla güncellediğini test eder."""
    mock_container = MagicMock()
    mock_settings = MagicMock()
    mock_settings.ai.gemini_api_key = ""
    mock_settings.evds.api_key = ""
    mock_container.settings = mock_settings

    ctrl = SettingsController(container=mock_container)
    ctrl.saveApiKeys("GEMINI_KEY_XYZ", "EVDS_KEY_123")

    assert mock_settings.ai.gemini_api_key == "GEMINI_KEY_XYZ"
    assert mock_settings.evds.api_key == "EVDS_KEY_123"
    assert ctrl.geminiApiKey == "GEMINI_KEY_XYZ"
    assert ctrl.evdsApiKey == "EVDS_KEY_123"


def test_settings_controller_db_stats(qapp):
    """refreshDatabaseStats slotunun SQLite ve DuckDB istatistiklerini doldurduğunu test eder."""
    from PySide6.QtCore import QCoreApplication
    ctrl = SettingsController(container=None)

    # Worker fonksiyonunu doğrudan çalıştır ve sinyali manuel tüket
    mock_payload = {}
    def capture(p):
        mock_payload.update(p)
    ctrl._asyncStatsReady.connect(capture)

    ctrl._run_db_stats_worker()
    QCoreApplication.processEvents()

    assert mock_payload.get("sqlite_size") != "0 B (Dosya Yok)"
    assert mock_payload.get("duckdb_size") != "0 B (Dosya Yok)"
    assert mock_payload.get("duckdb_stock_count", 0) >= 600
    assert len(mock_payload.get("sqlite_table_stats", [])) >= 5


def test_settings_controller_integrity_check():
    """checkDatabaseIntegrity slotunun SQLite ve DuckDB için başarıyla çalıştığını test eder."""
    ctrl = SettingsController(container=None)
    ctrl._run_integrity_worker()

    # Worker direkt çağrıldığında sinyal yayar, hata fırlatmaz
    assert ctrl._sqlite_path.exists()
    assert ctrl._duckdb_path.exists()


def test_settings_controller_export_portfolio(tmp_path):
    """Excel ve JSON dışa aktarım mekanizmasının sorunsuz çalıştığını test eder."""
    ctrl = SettingsController(container=None)

    # Test export worker
    ctrl._run_excel_export_worker()
    ctrl._run_json_export_worker()


def test_settings_qml_view_compilation(qapp, container):
    """SettingsView.qml dosyasının QML motorunda hatasız derlendiğini test eder."""
    engine = QQmlApplicationEngine()

    shell_ctrl = ShellController(container=container, parent=engine)
    chart_ctrl = ChartController(container=container, parent=engine)
    dash_ctrl = DashboardController(container=container, parent=engine)
    watchlist_ctrl = WatchlistController(container=container, parent=engine)
    stock_360_ctrl = Stock360Controller(container=container, parent=engine)
    portfolio_ctrl = ModelPortfolioController(container=container, parent=engine)
    comparison_ctrl = ComparisonController(container=container, parent=engine)
    screener_ctrl = ScreenerController(container=container, parent=engine)
    planning_ctrl = PlanningController(container=container, parent=engine)
    market_sync_ctrl = MarketSyncController(parent=engine)
    optimization_ctrl = OptimizationController(container=container, parent=engine)
    ai_advisor_ctrl = AiAdvisorController(container=container, parent=engine)
    settings_ctrl = SettingsController(container=container, parent=engine)

    ctx = engine.rootContext()
    ctx.setContextProperty("shellController", shell_ctrl)
    ctx.setContextProperty("chartController", chart_ctrl)
    ctx.setContextProperty("dashboardController", dash_ctrl)
    ctx.setContextProperty("watchlistController", watchlist_ctrl)
    ctx.setContextProperty("stock360Controller", stock_360_ctrl)
    ctx.setContextProperty("portfolioController", portfolio_ctrl)
    ctx.setContextProperty("comparisonController", comparison_ctrl)
    ctx.setContextProperty("screenerController", screener_ctrl)
    ctx.setContextProperty("planningController", planning_ctrl)
    ctx.setContextProperty("marketSyncController", market_sync_ctrl)
    ctx.setContextProperty("optimizationController", optimization_ctrl)
    ctx.setContextProperty("aiAdvisorController", ai_advisor_ctrl)
    ctx.setContextProperty("settingsController", settings_ctrl)

    qml_dir = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"
    engine.addImportPath(str(qml_dir))

    view_file = qml_dir / "views" / "SettingsView.qml"
    assert view_file.exists(), f"{view_file} bulunamadı!"

    component = QQmlComponent(engine, QUrl.fromLocalFile(str(view_file)))
    if not component.isReady():
        errors = [err.toString() for err in component.errors()]
        pytest.fail(f"SettingsView.qml derlenemedi:\n" + "\n".join(errors))

    item = component.create()
    assert item is not None, "SettingsView item nesnesi oluşturulamadı!"

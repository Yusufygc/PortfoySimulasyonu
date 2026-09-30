"""
Faz 4 İzleme Listeleri (Watchlist) Doğrulama Testi — Çoklu listeler, hisse tablosu,
mini sparkline verileri, CRUD işlemleri ve QML entegrasyonu.
"""
from __future__ import annotations

from pathlib import Path
import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineQuick import QtWebEngineQuick

from src.application.container import AppContainer
from src.ui_qml.controllers.shell_controller import ShellController
from src.ui_qml.controllers.chart_controller import ChartController
from src.ui_qml.controllers.dashboard_controller import DashboardController
from src.ui_qml.controllers.watchlist_controller import WatchlistController
from src.ui_qml.models.watchlist_table_model import WatchlistTableModel


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


def test_watchlist_controller_initialization(qapp, container):
    controller = WatchlistController(container)

    # En az 1 liste yüklenmiş olmalıdır
    assert len(controller.watchlists) > 0
    assert controller.currentWatchlistId > 0
    assert controller.currentWatchlistName != ""
    assert isinstance(controller.currentWatchlistCount, int)

    # Model doğrulaması
    model = controller.stocksModel
    assert isinstance(model, WatchlistTableModel)
    assert model.rowCount() >= 0


def test_watchlist_table_model_roles(qapp, container):
    controller = WatchlistController(container)
    model = controller.stocksModel

    if model.rowCount() > 0:
        idx = model.index(0, 0)
        ticker = model.data(idx, WatchlistTableModel.TickerRole)
        clean_ticker = model.data(idx, WatchlistTableModel.CleanTickerRole)
        price = model.data(idx, WatchlistTableModel.PriceRole)
        diff = model.data(idx, WatchlistTableModel.DailyDiffRole)
        sparkline = model.data(idx, WatchlistTableModel.SparklineRole)
        day_range = model.data(idx, WatchlistTableModel.DayRangePctRole)

        assert ticker != ""
        assert ".IS" not in clean_ticker
        assert "₺" in price
        assert "%" in diff
        assert isinstance(sparkline, list)
        assert 0.0 <= day_range <= 1.0


def test_watchlist_crud_operations(qapp, container):
    import uuid
    controller = WatchlistController(container)
    initial_count = len(controller.watchlists)

    unique_suffix = uuid.uuid4().hex[:6]
    test_list_name = f"Test Portfoy {unique_suffix}"

    try:
        # 1. Yeni Liste Oluşturma
        controller.createWatchlist(test_list_name, "Faz 4 otomatik test listesi")
        assert len(controller.watchlists) == initial_count + 1
        new_wl_id = controller.currentWatchlistId
        assert controller.currentWatchlistName == test_list_name

        # 2. Hisse Ekleme
        controller.addStock(new_wl_id, "THYAO", "Havacılık sektörü lideri")
        assert controller.stocksModel.rowCount() == 1

        first_idx = controller.stocksModel.index(0, 0)
        assert "THYAO" in controller.stocksModel.data(first_idx, WatchlistTableModel.TickerRole)
        assert controller.stocksModel.data(first_idx, WatchlistTableModel.NotesRole) == "Havacılık sektörü lideri"

        # 3. Not Güncelleme
        stock_id = controller.stocksModel.data(first_idx, WatchlistTableModel.StockIdRole)
        controller.updateStockNotes(new_wl_id, stock_id, "Hedef fiyat 350 TL")
        first_idx = controller.stocksModel.index(0, 0)
        assert controller.stocksModel.data(first_idx, WatchlistTableModel.NotesRole) == "Hedef fiyat 350 TL"

        # 4. Liste Adı Güncelleme
        updated_name = f"Test Guncel {unique_suffix}"
        controller.updateWatchlist(new_wl_id, updated_name, "Açıklama güncellendi")
        assert controller.currentWatchlistName == updated_name

        # 5. Hisseyi Listeden Çıkarma
        controller.removeStock(new_wl_id, stock_id)
        assert controller.stocksModel.rowCount() == 0

    finally:
        # 6. Listeyi Silme
        if controller.currentWatchlistId == new_wl_id:
            controller.deleteWatchlist(new_wl_id)
        assert len(controller.watchlists) == initial_count


def test_watchlist_qml_rendering(qapp, container):
    engine = QQmlApplicationEngine()

    shell_ctrl = ShellController(container, engine)
    chart_ctrl = ChartController(container, engine)
    dash_ctrl = DashboardController(container, engine)
    wl_ctrl = WatchlistController(container, engine)

    ctx = engine.rootContext()
    ctx.setContextProperty("shellController", shell_ctrl)
    ctx.setContextProperty("chartController", chart_ctrl)
    ctx.setContextProperty("dashboardController", dash_ctrl)
    ctx.setContextProperty("watchlistController", wl_ctrl)

    qml_dir = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"
    engine.addImportPath(str(qml_dir))

    main_qml = qml_dir / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(main_qml)))

    assert len(engine.rootObjects()) > 0
    win = engine.rootObjects()[0]

    # Watchlist sayfasına geçiş (Index: 1)
    shell_ctrl.navigateTo(1)
    assert shell_ctrl.activePage == 1

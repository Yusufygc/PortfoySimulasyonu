"""
test_stock_detail_and_excel.py — Hisse Detay Sayfası ve Excel Rapor Oluşturma Test Paketi.

Kapsam:
- StockDetailController ilklendirme ve durum özellikleri
- Hisse açma (openStock / openStockWithContext) ve .IS temizleme
- Gerçek portföy pozisyonu ve işlem geçmişi (tradesList) yükleme
- Sermaye artırımları (corpActionsList) yükleme
- Hisse detayından Excel (.xlsx) dışa aktarımı
- DashboardController Excel dışa aktarımı (exportToExcel)
- ModelPortfolioController Excel dışa aktarımı (exportToExcel)
- StockDetailModal.qml bileşeninin QML motorunda hatasız derlenmesi
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from decimal import Decimal
import pytest
from PySide6.QtCore import QUrl, QCoreApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from src.application.container import AppContainer
from src.ui_qml.controllers.stock_detail_controller import StockDetailController
from src.ui_qml.controllers.dashboard_controller import DashboardController
from src.ui_qml.controllers.model_portfolio_controller import ModelPortfolioController


@pytest.fixture(scope="module")
def container():
    return AppContainer()


def wait_until(condition, timeout=3.0):
    """Asenkron işlemler için Qt event loop'u çalıştırarak koşulun sağlanmasını bekler."""
    start = time.time()
    while not condition() and time.time() - start < timeout:
        time.sleep(0.03)
        QCoreApplication.processEvents()
    return condition()


def test_stock_detail_controller_init():
    """StockDetailController varsayılan durumunu test eder."""
    ctrl = StockDetailController(container=None)
    assert ctrl.isOpen is False
    assert ctrl.isLoading is False
    assert ctrl.ticker == ""
    assert ctrl.currentPrice == 0.0
    assert ctrl.quantity == 0
    assert ctrl.avgCost == 0.0
    assert ctrl.tradesList == []
    assert ctrl.corpActionsList == []


def test_stock_detail_controller_clean_ticker(qapp, container):
    """Hisse açıldığında .IS uzantısının temizlendiğini ve isOpen olduğunu doğrular."""
    ctrl = StockDetailController(container=container)
    ctrl.openStock("THYAO.IS")

    assert ctrl.isOpen is True
    assert ctrl.ticker == "THYAO"
    assert ".IS" not in ctrl.ticker


def test_stock_detail_controller_load_position(qapp, container):
    """Portföyde var olan hissenin pozisyon ve işlem verilerini yüklemesini test eder."""
    ctrl = StockDetailController(container=container)
    ctrl.openStock("OBAMS")

    assert wait_until(lambda: not ctrl.isLoading and ctrl.quantity > 0), "OBAMS verileri yüklenemedi!"

    assert ctrl.ticker == "OBAMS"
    assert ctrl.quantity > 0
    assert ctrl.avgCost > 0.0
    assert ctrl.marketValue > 0.0
    assert len(ctrl.tradesList) >= 1

    first_trade = ctrl.tradesList[0]
    assert "date" in first_trade
    assert "side" in first_trade
    assert "quantity" in first_trade
    assert "price" in first_trade


def test_stock_detail_controller_corporate_actions(qapp, container):
    """Sermaye artırımı bulunan hissede (MERKO) kurumsal işlemlerin çekildiğini doğrular."""
    ctrl = StockDetailController(container=container)
    ctrl.openStock("MERKO")

    assert wait_until(lambda: not ctrl.isLoading and len(ctrl.corpActionsList) > 0), "MERKO sermaye artırımları yüklenemedi!"

    assert ctrl.ticker == "MERKO"
    assert len(ctrl.corpActionsList) >= 1
    action = ctrl.corpActionsList[0]
    assert "BEDELSIZ" in action.get("actionType", "") or "BEDELLI" in action.get("actionType", "")
    assert "%" in action.get("ratioStr", "")


def test_stock_detail_controller_export_excel(qapp, container):
    """Hisse detayından Excel dışa aktarımının çalıştığını doğrular."""
    ctrl = StockDetailController(container=container)
    ctrl.openStock("OBAMS")

    assert wait_until(lambda: not ctrl.isLoading and ctrl.quantity > 0), "OBAMS yüklenemedi!"

    exported_results = []
    ctrl.excelExported.connect(lambda s, m: exported_results.append((s, m)))

    ctrl.exportStockToExcel()
    assert wait_until(lambda: len(exported_results) > 0), "Excel aktarımı tamamlanamadı!"

    success, message = exported_results[0]
    assert success is True
    assert "OBAMS" in message


def test_dashboard_controller_export_to_excel(qapp, container):
    """DashboardController üzerinden Excel raporu oluşturulabildiğini test eder."""
    dash = DashboardController(container=container)

    results = []
    dash.excelExported.connect(lambda s, m: results.append((s, m)))

    dash.exportToExcel()
    assert wait_until(lambda: len(results) > 0), "Dashboard Excel aktarımı tamamlanamadı!"

    success, message = results[0]
    assert success is True
    assert ".xlsx" in message


def test_model_portfolio_controller_export_to_excel(qapp, container):
    """ModelPortfolioController üzerinden model portföyün Excel'e aktarılabildiğini test eder."""
    port_ctrl = ModelPortfolioController(container=container)
    port_ctrl.refreshData()

    if not port_ctrl._portfolio_list:
        pytest.skip("Model portföy bulunamadı.")

    p_id = port_ctrl._portfolio_list[0]["portfolioId"]
    port_ctrl.selectPortfolio(p_id)

    results = []
    port_ctrl.excelExported.connect(lambda s, m: results.append((s, m)))

    port_ctrl.exportToExcel()
    assert wait_until(lambda: len(results) > 0), "Model portföy Excel aktarımı tamamlanamadı!"

    success, message = results[0]
    assert success is True
    assert ".xlsx" in message


def test_stock_detail_modal_qml_compilation(qapp, container):
    """StockDetailModal.qml dosyasının QML motorunda hatasız derlenip oluşturulduğunu doğrular."""
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
    engine = QQmlApplicationEngine()

    qml_dir = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"
    engine.addImportPath(str(qml_dir))

    ctrl = StockDetailController(container=container, parent=engine)
    engine.rootContext().setContextProperty("stockDetailController", ctrl)

    qml_path = qml_dir / "components" / "StockDetailModal.qml"
    assert qml_path.exists(), f"Dosya bulunamadı: {qml_path}"

    component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml_path)))
    if not component.isReady():
        errors = [err.toString() for err in component.errors()]
        pytest.fail(f"StockDetailModal.qml derlenemedi:\n" + "\n".join(errors))

    obj = component.create()
    assert obj is not None, "StockDetailModal QML nesnesi oluşturulamadı!"

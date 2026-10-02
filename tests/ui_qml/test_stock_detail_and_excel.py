"""
test_stock_detail_and_excel.py — Hisse Detay Sayfası ve Excel Rapor Oluşturma Test Paketi.

Kapsam:
- StockDetailController ilklendirme ve durum özellikleri
- Hisse açma (openStock / openStockWithContext) ve .IS temizleme
- Gerçek portföy pozisyonu ve işlem geçmişi (tradesList) yükleme
- Sermaye artırımları (corpActionsList) yükleme
- Hisse detayından Excel (.xlsx) dışa aktarımı
- DashboardController Excel dışa aktarımı (exportToExcelFile)
- ModelPortfolioController Excel dışa aktarımı (exportHistoryToFile)
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


def wait_until(condition, timeout=15.0):
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


def test_dashboard_controller_export_to_excel(qapp, container, tmp_path):
    """DashboardController üzerinden Excel raporu oluşturulabildiğini test eder."""
    dash = DashboardController(container=container)

    results = []
    dash.excelExported.connect(lambda s, m: results.append((s, m)))

    dash.exportToExcelFile("", "", str(tmp_path / "Portfoy_Raporu.xlsx"), False)
    assert wait_until(lambda: len(results) > 0), "Dashboard Excel aktarımı tamamlanamadı!"

    success, message = results[0]
    assert success is True
    assert ".xlsx" in message


def test_model_portfolio_controller_export_to_excel(qapp, container, tmp_path):
    """ModelPortfolioController üzerinden model portföyün Excel'e aktarılabildiğini test eder."""
    port_ctrl = ModelPortfolioController(container=container)
    port_ctrl.refreshData()

    if not port_ctrl._portfolio_list:
        pytest.skip("Model portföy bulunamadı.")

    p_id = port_ctrl._portfolio_list[0]["portfolioId"]
    port_ctrl.selectPortfolio(p_id)

    results = []
    port_ctrl.excelExported.connect(lambda s, m: results.append((s, m)))

    port_ctrl.exportHistoryToFile("", "", str(tmp_path / "Model_Portfoy.xlsx"), False)
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


def test_stock_detail_controller_live_price_and_diff(container):
    """StockDetailController canlı fiyat ve günlük farkı hesaplayıp PnL ile eşleştirir.

    Gerçek piyasa verisi zamanla değiştiği için beklenen değerler sabit sayı yerine aynı
    repository'lerden hesaplanır.
    """
    from datetime import timedelta

    stock = container.stock_repo.get_stock_by_ticker("MERKO.IS")
    assert stock is not None
    resolved = container.current_price_resolver.resolve([stock.id])[stock.id]
    latest = resolved.price
    previous = container.price_repo.get_last_price_before(stock.id, resolved.price_date - timedelta(days=1))
    assert latest and previous

    ctrl = StockDetailController(container=container)
    ctrl.openStock("MERKO")

    assert wait_until(lambda: ctrl.currentPrice > 0, timeout=5.0)
    assert ctrl.currentPrice == pytest.approx(float(latest), rel=1e-6)
    expected_diff = (float(latest) - float(previous.close_price)) / float(previous.close_price) * 100
    assert ctrl.dailyDiff == pytest.approx(expected_diff, abs=0.01)
    # Açık pozisyon değerleri
    assert ctrl.quantity > 0
    assert ctrl.marketValue > 0
    assert ctrl.isPnlPositive == (ctrl._unrealized_pnl >= 0)


def test_dashboard_controller_no_dot_is(container):
    """DashboardController quickTickers ve allocationSlices içinde kesinlikle .IS bulunmadığını doğrular."""
    dash = DashboardController(container=container)
    dash._load_portfolio_data()

    # quickTickers içinde .IS olmamalı
    for t in dash.quickTickers:
        assert not t.endswith(".IS"), f"quickTickers içinde .IS bulundu: {t}"

    # allocationSlices içinde .IS olmamalı
    for s in dash.allocationSlices:
        lbl = s.get("label", "")
        assert not lbl.endswith(".IS"), f"allocationSlices label içinde .IS bulundu: {lbl}"


"""
Faz 5 Hisse 360 & Temel Analiz Doğrulama Testi — Rasyolar, Çeyreklik Bilanço Grafiği,
KAP Ortaklık Yapısı, Genel Bakış, Teknik Seviyeler ve QML Entegrasyonu.
"""
from __future__ import annotations

import time
from pathlib import Path
import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineQuick import QtWebEngineQuick

from src.application.container import AppContainer
from src.ui_qml.controllers.shell_controller import ShellController
from src.ui_qml.controllers.chart_controller import ChartController
from src.ui_qml.controllers.dashboard_controller import DashboardController
from src.ui_qml.controllers.watchlist_controller import WatchlistController
from src.ui_qml.controllers.stock_360_controller import Stock360Controller


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


def test_stock_360_controller_initialization(qapp, container):
    """Stock360Controller'ın başarıyla başlatıldığını ve varsayılan verilerini doğrula."""
    ctrl = Stock360Controller(container)

    assert ctrl.currentTicker != ""
    assert ctrl.companyName != ""
    assert ctrl.sector != ""
    assert "₺" in ctrl.lastPrice or ctrl.lastPrice != ""
    assert isinstance(ctrl.lastPriceRaw, float)
    assert "%" in ctrl.dailyChange
    assert ctrl.volume != ""
    assert 0.0 <= ctrl.week52RangePct <= 1.0

    # Teknik seviyeler
    assert ctrl.rsi14 != ""
    assert ctrl.rsiStatus != ""
    assert ctrl.trendStatus != ""

    # Hızlı hisse listesi
    assert len(ctrl.availableStocks) > 0
    assert "BIMAS" in ctrl.availableStocks or "ADEL" in ctrl.availableStocks


def test_stock_360_controller_search_and_switch(qapp, container):
    """Farklı hisse senetleri arasında geçiş ve temizleme işlemlerini test et."""
    ctrl = Stock360Controller(container)

    # 1. ADEL araması
    ctrl.searchTicker("ADEL")
    assert ctrl.currentTicker == "ADEL"
    assert "₺" in ctrl.lastPrice

    # 2. .IS soneki ile arama
    ctrl.searchTicker("AKCNS.IS")
    assert ctrl.currentTicker == "AKCNS"

    # 3. Küçük harf arama
    ctrl.searchTicker("bimas")
    assert ctrl.currentTicker == "BIMAS"


def test_stock_360_controller_financial_tabs(qapp, container):
    """Çeyreklik bilanço metrik sekmeleri ve çubuk grafik verilerini test et."""
    ctrl = Stock360Controller(container)

    # Arka plan iş parçacığının sonuçları işlemesi için kısa bir bekleme ve event işleme
    time.sleep(1.5)
    qapp.processEvents()

    # Varsayılan sekme
    assert ctrl.activeFinancialTab == "satis"

    # Brüt Kâr sekmesine geçiş
    ctrl.setFinancialTab("brut_kar")
    assert ctrl.activeFinancialTab == "brut_kar"
    assert isinstance(ctrl.financialBars, list)

    # FAVÖK sekmesine geçiş
    ctrl.setFinancialTab("favok")
    assert ctrl.activeFinancialTab == "favok"

    # Net Kâr sekmesine geçiş
    ctrl.setFinancialTab("net_kar")
    assert ctrl.activeFinancialTab == "net_kar"

    # Çubukların alanlarını doğrula
    if ctrl.financialBars:
        bar = ctrl.financialBars[0]
        assert "period" in bar
        assert "value" in bar
        assert "amount" in bar
        assert "ratio" in bar
        assert "isPositive" in bar


def test_stock_360_controller_shareholders(qapp, container):
    """KAP Ortaklık Yapısı ve Halka Açıklık Oranı verilerini doğrula."""
    ctrl = Stock360Controller(container)

    time.sleep(1.5)
    qapp.processEvents()

    assert isinstance(ctrl.shareholdersList, list)
    assert isinstance(ctrl.shareholderSlices, list)

    if ctrl.shareholdersList:
        item = ctrl.shareholdersList[0]
        assert "name" in item
        assert "ratio" in item
        assert "ratioStr" in item
        assert "share" in item
        assert "color" in item

    if ctrl.shareholderSlices:
        slice_item = ctrl.shareholderSlices[0]
        assert "label" in slice_item
        assert "pct" in slice_item
        assert "color" in slice_item

    assert ctrl.freeFloatRatio != ""


def test_stock_360_qml_full_rendering(qapp, container):
    """Main.qml üzerinden Hisse 360 sayfasına geçişi ve hatasız render edilmesini test et."""
    engine = QQmlApplicationEngine()

    shell_ctrl = ShellController(container, engine)
    chart_ctrl = ChartController(container, engine)
    dash_ctrl = DashboardController(container, engine)
    wl_ctrl = WatchlistController(container, engine)
    s360_ctrl = Stock360Controller(container, engine)

    ctx = engine.rootContext()
    ctx.setContextProperty("shellController", shell_ctrl)
    ctx.setContextProperty("chartController", chart_ctrl)
    ctx.setContextProperty("dashboardController", dash_ctrl)
    ctx.setContextProperty("watchlistController", wl_ctrl)
    ctx.setContextProperty("stock360Controller", s360_ctrl)

    qml_dir = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"
    engine.addImportPath(str(qml_dir))

    warnings_list = []
    engine.warnings.connect(lambda warns: warnings_list.extend([w.toString() for w in warns]))

    main_qml = qml_dir / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(main_qml)))

    assert len(engine.rootObjects()) > 0, f"Main.qml yüklenemedi! Uyarılar: {warnings_list}"

    # Hisse 360 sayfasına geçiş (Index: 3)
    shell_ctrl.navigateTo(3)
    assert shell_ctrl.activePage == 3
    qapp.processEvents()


def test_stock_360_individual_components_rendering(qapp, container):
    """RatioCard, FinancialBarChart ve ShareholderPieCard bileşenlerinin bağımsız yüklenebildiğini doğrula."""
    engine = QQmlApplicationEngine()
    s360_ctrl = Stock360Controller(container, engine)
    engine.rootContext().setContextProperty("stock360Controller", s360_ctrl)

    qml_dir = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"
    engine.addImportPath(str(qml_dir))

    comp = QQmlComponent(engine)
    test_qml = """
    import QtQuick
    import "src/ui_qml/qml/components"
    import "src/ui_qml/qml/theme"

    Item {
        width: 800
        height: 600

        RatioCard {
            title: "F/K"
            value: "13.4"
            subtitle: "Fiyat / Kazanç"
            badgeText: "Değerleme"
        }

        FinancialBarChart {
            width: 400
            height: 300
        }

        ShareholderPieCard {
            width: 350
            height: 300
        }
    }
    """
    comp.setData(test_qml.encode("utf-8"), QUrl.fromLocalFile(str(Path.cwd() / "test_comp.qml")))
    assert not comp.errors(), f"QML Hataları: {comp.errors()}"
    obj = comp.create()
    assert obj is not None


def test_stock_360_view_modes_and_periods(qapp, container):
    """Görünüm modları (Genel Bakış, 18 Modüllü Bilanço, KAP Tarihçesi) ve çeyrek seçimlerini test et."""
    ctrl = Stock360Controller(container)

    # Varsayılan mod: 0 (Genel Bakış)
    assert ctrl.viewMode == 0
    assert ctrl.periodsCount == 8

    # Mod 1: Kapsamlı Bilanço & 18 Analiz Modülü
    ctrl.setViewMode(1)
    assert ctrl.viewMode == 1

    # Çeyrek dönem değiştirme: 4 çeyrek
    ctrl.setFinancialsPeriods(4)
    assert ctrl.periodsCount == 4

    # Mod 2: KAP Ortaklık Tarihçesi
    ctrl.setViewMode(2)
    assert ctrl.viewMode == 2

    # Mod 0'a geri dönüş
    ctrl.setViewMode(0)
    assert ctrl.viewMode == 0


def test_financials_dashboard_view_component(qapp, container):
    """FinancialsDashboardView bileşeninin hatasız derlenip render edildiğini doğrula."""
    engine = QQmlApplicationEngine()
    s360_ctrl = Stock360Controller(container, engine)
    engine.rootContext().setContextProperty("stock360Controller", s360_ctrl)

    qml_dir = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"
    engine.addImportPath(str(qml_dir))

    comp = QQmlComponent(engine)
    test_qml = """
    import QtQuick
    import "src/ui_qml/qml/components"
    import "src/ui_qml/qml/theme"

    Item {
        width: 800
        height: 600

        FinancialsDashboardView {
            anchors.fill: parent
            htmlUrl: ""
            isLoading: false
        }
    }
    """
    comp.setData(test_qml.encode("utf-8"), QUrl.fromLocalFile(str(Path.cwd() / "test_fin_dash.qml")))
    assert not comp.errors(), f"QML Hataları: {comp.errors()}"
    obj = comp.create()
    assert obj is not None

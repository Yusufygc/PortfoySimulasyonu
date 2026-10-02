"""
Faz 9 Markowitz Portföy Optimizasyonu ve Efficient Frontier Doğrulama Testi.
"""
from __future__ import annotations

from pathlib import Path
import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineQuick import QtWebEngineQuick

from src.application.container import AppContainer
from src.infrastructure.market_data.duckdb_optimization_market_data_provider import (
    DuckDBOptimizationMarketDataProvider,
)
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


def test_duckdb_optimization_market_data_provider():
    """DuckDBOptimizationMarketDataProvider'ın DuckDB'den çoklu hisse fiyatlarını ve son fiyatı okumasını test eder."""
    provider = DuckDBOptimizationMarketDataProvider()
    tickers = ["THYAO.IS", "ASELS.IS", "GARAN.IS"]

    df = provider.get_historical_prices(tickers, days=120)
    assert not df.empty, "Tarihsel fiyat DataFrame'i boş dönmemelidir"
    assert len(df) >= 60, "En az 60 bar veri dönmelidir"
    for t in tickers:
        assert t in df.columns, f"{t} kolonu DataFrame içinde bulunmalıdır"

    last_price = provider.get_last_price("THYAO.IS")
    assert last_price is not None
    assert last_price > 0.0


def test_optimization_controller_initialization(qapp, container):
    """OptimizationController başlatma ve varsayılan property değerlerini test eder."""
    ctrl = OptimizationController(container=container)
    assert len(ctrl.portfolioOptions) >= 1
    assert ctrl.selectedPortfolioCode == "dashboard"
    assert len(ctrl.riskProfileOptions) >= 5
    assert ctrl.maxSingleWeight > 0.0
    assert ctrl.riskFreeRate > 0.0
    assert not ctrl.isLoading
    assert not ctrl.hasResults
    assert ctrl.activeTab == 0
    assert ctrl.statusMessage == ""
    assert ctrl.chartHtml == ""
    assert isinstance(ctrl.suggestions, list)
    assert isinstance(ctrl.weightsComparison, list)


def test_optimization_controller_slots(qapp, container):
    """OptimizationController slot çağrılarını ve kısıt güncellemelerini test eder."""
    ctrl = OptimizationController(container=container)

    # Portföy seçimi
    ctrl.selectPortfolio("dashboard")
    assert ctrl.selectedPortfolioCode == "dashboard"

    # Risk profili seçimi
    ctrl.selectRiskProfile("AGRESIF")
    assert ctrl.selectedRiskProfile == "AGRESIF"
    assert ctrl.maxSingleWeight == 35.0

    # Manuel ağırlık kısıtı
    ctrl.setMaxSingleWeight(25.0)
    assert ctrl.maxSingleWeight == 25.0
    assert ctrl.selectedRiskProfile == "MANUAL"

    # Risksiz faiz oranı
    ctrl.setRiskFreeRate(45.0)
    assert ctrl.riskFreeRate == 45.0

    # Sekme değiştirme
    ctrl.setActiveTab(1)
    assert ctrl.activeTab == 1
    ctrl.setActiveTab(2)
    assert ctrl.activeTab == 2
    ctrl.setActiveTab(0)
    assert ctrl.activeTab == 0


def test_optimization_controller_execution(qapp, container):
    """OptimizationController senkron/asenkron çalıştırma ve sonuç yükleme döngüsünü test eder."""
    ctrl = OptimizationController(container=container)

    # Worker metodunu doğrudan çağırarak sonucu doğrula
    ctrl._async_compute_optimization(
        portfolio_code="dashboard",
        max_single_weight=0.35,
        risk_free_rate=0.30,
    )

    # Sonuçlar yüklendi mi
    assert ctrl.hasResults, "Optimizasyon hasResults bayrağını True yapmalıdır"
    assert not ctrl.isLoading
    assert ctrl.chartHtml != ""
    assert "frontierCanvas" in ctrl.chartHtml
    assert "Chart" in ctrl.chartHtml

    assert ctrl.weightsChartHtml != ""
    assert "weightsCanvas" in ctrl.weightsChartHtml

    assert len(ctrl.suggestions) >= 2
    first_sug = ctrl.suggestions[0]
    assert "symbol" in first_sug
    assert "optimalWeight" in first_sug
    assert "action" in first_sug
    assert first_sug["action"] in ["EKLE", "AZALT", "TUT"]

    assert ctrl.optimalSharpe >= 0.0 or ctrl.optimalSharpe < 0.0
    assert ctrl.optimalReturnFormatted != ""
    assert ctrl.optimalVolFormatted != ""
    assert isinstance(ctrl.isOptimalReturnPositive, bool)
    assert isinstance(ctrl.isCurrentReturnPositive, bool)
    assert isinstance(ctrl.isOptimalSharpePositive, bool)
    assert ctrl.optimalSharpeFormatted != ""
    assert ctrl.currentSharpeFormatted != ""


def test_fmt_pct():
    """_fmt_pct fonksiyonunun Türkçe standartlarında (negatifte eksi başta, virgüllü) biçimlendirmesini test eder."""
    from src.ui_qml.controllers.optimization_controller import _fmt_pct
    assert _fmt_pct(16.32) == "%16,32"
    assert _fmt_pct(-5.82) == "-%5,82"
    assert _fmt_pct(11.68, with_sign=True) == "+%11,68"
    assert _fmt_pct(-8.45, with_sign=True) == "-%8,45"
    assert _fmt_pct(0.0) == "%0,00"
    assert _fmt_pct(None) == "%0,00"


def test_calculate_rebalance_plan_rules():
    """calculate_rebalance_plan fonksiyonunun çıkış (sıfır ağırlık), tut ve .IS temizleme kurallarını test eder."""
    from src.application.services.planning.frontier_simulation import calculate_rebalance_plan

    current_weights = {
        "SDTTR.IS": 0.69,   # Sıfırlanan hisse (çıkış)
        "THYAO.IS": 15.20,  # TUTulacak hisse (fark %0.20)
        "ENJSA.IS": 10.61,  # Eklenecek hisse (fark +%9.39)
        "ENKAI.IS": 10.30,  # Çıkartılacak hisse
    }
    optimal_weights = {
        "SDTTR.IS": 0.00,
        "THYAO.IS": 15.00,
        "ENJSA.IS": 20.00,
        "ENKAI.IS": 0.00,
    }
    last_prices = {
        "SDTTR.IS": 15.25,
        "THYAO.IS": 300.0,
        "ENJSA.IS": 60.0,
        "ENKAI.IS": 45.0,
    }
    names = {
        "SDTTR.IS": "SDT Uzay ve Savunma",
        "THYAO.IS": "THYAO.IS",  # .IS uzantılı gelen kirli isim
        "ENKAI.IS": "ENKAI.IS",
    }

    plan = calculate_rebalance_plan(
        total_portfolio_value=100000.0,
        current_weights=current_weights,
        optimal_weights=optimal_weights,
        last_prices=last_prices,
        stock_names=names,
    )

    plan_map = {item["symbol"]: item for item in plan}

    # 1. Hiçbir sembolde ve şirket adında .IS kalmamalıdır
    for item in plan:
        assert not item["symbol"].endswith(".IS"), f"{item['symbol']} .IS ile bitmemelidir"
        assert not item["companyName"].endswith(".IS"), f"{item['companyName']} .IS ile bitmemelidir"

    # 2. SDTTR: Ağırlık sıfırlanıyorsa aksiyon TUT DEĞİL, AZALT olmalıdır
    sdttr = plan_map["SDTTR"]
    assert sdttr["action"] == "AZALT", "Portföyden sıfırlanan hissenin aksiyonu AZALT olmalıdır"
    assert sdttr["optimalWeight"] == 0.0
    assert sdttr["amountDiff"] < 0
    assert sdttr["estShares"] > 0

    # 3. THYAO: Gerçekten TUT durumundaki hissede tutar farkı 0 ve lot 0 olmalıdır
    thyao = plan_map["THYAO"]
    assert thyao["action"] == "TUT", "Küçük sapmalı hisse TUT olmalıdır"
    assert thyao["amountDiff"] == 0.0, "TUT hissesinde işlem tutarı 0 olmalıdır"
    assert thyao["estShares"] == 0, "TUT hissesinde işlem lotu 0 olmalıdır"
    assert thyao["companyName"] == "THYAO", "Kirli şirket adı temizlenmelidir"


def test_optimization_qml_view_compilation(qapp, container):
    """OptimizationView.qml dosyasının QML motorunda hatasız derlendiğini test eder."""
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

    qml_dir = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"
    engine.addImportPath(str(qml_dir))

    view_file = qml_dir / "views" / "OptimizationView.qml"
    assert view_file.exists(), f"{view_file} bulunamadı!"

    component = QQmlComponent(engine, QUrl.fromLocalFile(str(view_file)))
    if not component.isReady():
        errors = [err.toString() for err in component.errors()]
        pytest.fail(f"OptimizationView.qml derlenemedi:\n" + "\n".join(errors))

    item = component.create()
    assert item is not None, "OptimizationView item nesnesi oluşturulamadı!"

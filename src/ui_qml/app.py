"""
QML Uygulama Giriş Noktası — PySide6, QtQuick ve WebEngine tabanlı modern UI çalıştırıcısı.
"""
from __future__ import annotations

import sys
import logging
from pathlib import Path
from typing import Any, Dict

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWebEngineQuick import QtWebEngineQuick
from PySide6.QtQuickControls2 import QQuickStyle

from src.ui_qml.controllers.shell_controller import ShellController
from src.ui_qml.controllers.chart_controller import ChartController
from src.ui_qml.controllers.dashboard_controller import DashboardController
from src.ui_qml.controllers.my_portfolio_controller import MyPortfolioController
from src.ui_qml.controllers.assets_controller import AssetsController
from src.ui_qml.controllers.watchlist_controller import WatchlistController
from src.ui_qml.controllers.stock_360_controller import Stock360Controller
from src.ui_qml.controllers.model_portfolio_controller import ModelPortfolioController
from src.ui_qml.controllers.comparison_controller import ComparisonController
from src.ui_qml.controllers.screener_controller import ScreenerController
from src.ui_qml.controllers.planning_controller import PlanningController
from src.ui_qml.controllers.strategy_backtest_controller import StrategyBacktestController
from src.ui_qml.controllers.market_sync_controller import MarketSyncController
from src.ui_qml.controllers.optimization_controller import OptimizationController
from src.ui_qml.controllers.ai_advisor_controller import AiAdvisorController
from src.ui_qml.controllers.settings_controller import SettingsController
from src.ui_qml.controllers.stock_detail_controller import StockDetailController
from src.ui_qml.controllers.corporate_action_controller import CorporateActionController
from src.ui_qml.controllers.dividend_controller import DividendController
from src.ui_qml.controllers.market_adjustment_controller import MarketAdjustmentController
from src.ui_qml.controllers.system_controller import SystemController
from src.ui_qml.controllers.market_ticker_controller import MarketTickerController
from src.ui_qml.controllers.news_controller import NewsController
from src.ui_qml.controllers.cash_pool_controller import CashPoolController
from src.ui_qml.controllers.fee_settings_controller import FeeSettingsController
from src.ui_qml.controllers.news_settings_controller import NewsSettingsController
from src.ui_qml.controllers.model_analysis_controller import ModelAnalysisController
from src.ui_qml.controllers.price_data_controller import PriceDataController
from src.ui_qml.controllers.price_refresh_controller import PriceRefreshController
from src.ui_qml.controllers.startup_jobs_controller import StartupJobsController
from src.ui_qml.controllers.golden_cross_controller import GoldenCrossController
from src.ui_qml.controllers.risk_profile_controller import RiskProfileController

logger = logging.getLogger(__name__)

QML_DIR = Path(__file__).resolve().parent / "qml"


def _wire_price_refresh(price_refresh_ctrl, dash_ctrl, portfolio_ctrl, watchlist_ctrl, my_portfolio_ctrl=None) -> None:
    """Birleştirilmiş fiyat değişikliği: öncelik sırasıyla Ana Sayfa, Portföyüm, İzleme Listesi, Model Portföy DB'den yeniden okunur."""
    price_refresh_ctrl.pricesChanged.connect(dash_ctrl.reloadPrices)
    if my_portfolio_ctrl is not None:
        price_refresh_ctrl.pricesChanged.connect(my_portfolio_ctrl.reloadPrices)
    price_refresh_ctrl.pricesChanged.connect(watchlist_ctrl.refreshPrices)
    price_refresh_ctrl.pricesChanged.connect(portfolio_ctrl.reloadPrices)


def create_controllers(container, parent, autostart: bool = True) -> Dict[str, Any]:
    """Tüm denetleyicileri QML bağlam adlarıyla kurar. `autostart=False` zamanlayıcıları başlatmaz (testler)."""
    def make(cls, **kwargs):
        return cls(container=container, parent=parent, **kwargs)

    controllers: Dict[str, Any] = {
        "shellController": make(ShellController),
        "chartController": make(ChartController),
        "dashboardController": make(DashboardController),
        "myPortfolioController": make(MyPortfolioController),
        "assetsController": make(AssetsController, autostart=autostart),
        "watchlistController": make(WatchlistController),
        "stock360Controller": make(Stock360Controller),
        "portfolioController": make(ModelPortfolioController),
        "comparisonController": make(ComparisonController),
        "screenerController": make(ScreenerController),
        "planningController": make(PlanningController),
        "strategyBacktestController": make(StrategyBacktestController),
        "marketSyncController": make(MarketSyncController),
        "optimizationController": make(OptimizationController),
        "aiAdvisorController": make(AiAdvisorController),
        "settingsController": make(SettingsController),
        "stockDetailController": make(StockDetailController),
        "corporateActionController": make(CorporateActionController),
        "dividendController": make(DividendController),
        "priceDataController": make(PriceDataController),
        "startupJobsController": make(StartupJobsController, autostart=False),
        "goldenCrossController": make(GoldenCrossController),
        "riskProfileController": make(RiskProfileController),
        "marketAdjustmentController": make(MarketAdjustmentController),
        "systemController": make(SystemController),
        "marketTickerController": make(MarketTickerController),
        "newsController": make(NewsController, autostart=autostart),
        "newsSettingsController": make(NewsSettingsController),
        "feeSettingsController": make(FeeSettingsController),
        "cashPoolController": make(CashPoolController),
        "modelAnalysisController": make(ModelAnalysisController),
    }
    controllers["priceRefreshController"] = PriceRefreshController(
        controllers["systemController"], controllers["marketSyncController"], container=container, parent=parent
    )
    return controllers


def wire_controllers(c: Dict[str, Any]) -> None:
    """Denetleyiciler arası sinyal bağlantıları (fiyat, portföy, varlık ve haber değişiklikleri)."""
    news, my_portfolio, models = c["newsController"], c["myPortfolioController"], c["portfolioController"]
    refresh, system = c["priceRefreshController"], c["systemController"]
    c["newsSettingsController"].sourcesChanged.connect(news.refresh)  # kapatılan/açılan kaynak panele hemen yansır
    c["newsSettingsController"].refreshMinutesChanged.connect(news.setRefreshMinutes)
    # Açılış kapanış tamamlaması ilk BIST senkronundan sonra: aynı kapanışlar iki yoldan eşzamanlı indirilmesin
    c["startupJobsController"].start_after(c["marketSyncController"].syncFinished)
    _wire_price_refresh(refresh, c["dashboardController"], models, c["watchlistController"], my_portfolio)
    cash_pool = c["cashPoolController"]
    for target in (my_portfolio.reload, news.refresh, c["chartController"].refreshAssets, cash_pool.reload,
                   c["dashboardController"].reloadPortfolio):  # varlık defteri değişti: TL/USD nakit de değişir
        c["assetsController"].dataChanged.connect(target)
    for target in (my_portfolio.reload, c["dashboardController"].reloadPortfolio):  # döviz al/sat: nakit havuzu değişti
        cash_pool.balancesChanged.connect(target)
    for source in (c["dashboardController"].tradeExecuted, c["dashboardController"].capitalUpdated):  # BIST işlemi/sermaye
        source.connect(lambda *_: cash_pool.reload())
    for source in (c["marketSyncController"].dataSynced, system.pricesRefreshed, c["startupJobsController"].pricesUpdated,
                   c["priceDataController"].pricesUpdated, c["goldenCrossController"].pricesUpdated):
        refresh.watch(source)
    # Portföy içeriği değişti (fiyat değil): son güncelleme zamanı değişmez, liste/özet yeniden okunur
    for source in (c["corporateActionController"].portfolioChanged, c["dividendController"].portfolioChanged,
                   system.systemReset):
        refresh.watch(source, records_update=False)
        for target in (models.refreshData, my_portfolio.reload, news.refresh):
            source.connect(target)
    system.systemReset.connect(c["watchlistController"].reloadAll)
    c["riskProfileController"].profileSaved.connect(c["optimizationController"].reloadRiskProfile)


def build_ui(engine, container, autostart: bool = True) -> Dict[str, Any]:
    """Bileşim kökü: denetleyicileri kurar, bağlar ve QML bağlamına kaydeder (Main.qml yüklenmez)."""
    controllers = create_controllers(container, engine, autostart=autostart)
    wire_controllers(controllers)
    context = engine.rootContext()
    for name, controller in controllers.items():
        context.setContextProperty(name, controller)
    engine.addImportPath(str(QML_DIR))
    return controllers


def _fit_window_to_screen(app, engine) -> None:
    """Ekran çözünürlüğüne göre pencereyi otomatik sınırla ve ekranda merkeze al."""
    primary_screen = app.primaryScreen()
    if not primary_screen:
        return
    geom = primary_screen.availableGeometry()
    win = engine.rootObjects()[0]
    w = max(960, min(int(win.property("width") or 1200), geom.width() - 40))
    h = max(600, min(int(win.property("height") or 760), geom.height() - 60))
    win.setProperty("width", w)
    win.setProperty("height", h)
    win.setProperty("x", geom.x() + max(0, (geom.width() - w) // 2))
    win.setProperty("y", geom.y() + max(0, (geom.height() - h) // 2))


def run_qml_app(container=None) -> int:
    """QML tabanlı modern arayüzü başlatır."""
    # Modern özel bileşenlerin ve kaydırma çubuklarının (ScrollBar) native stil tarafından ezilmemesi için Basic stil ayarlanır
    QQuickStyle.setStyle("Basic")

    # WebEngineQuick başlatması (QApplication öncesi veya hemen başında çağrılmalıdır)
    QtWebEngineQuick.initialize()

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setApplicationName("PortfoySimulasyonu")
    app.setOrganizationName("PortfoySim")

    engine = QQmlApplicationEngine()

    # DI Container
    if container is None:
        try:
            from src.application.container import AppContainer
            container = AppContainer()
        except Exception as exc:
            logger.warning("Container başlatılamadı, mock/offline modda devam ediliyor: %s", exc)

    build_ui(engine, container)
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    if not engine.rootObjects():
        logger.error("Main.qml yüklenemedi!")
        return -1
    _fit_window_to_screen(app, engine)

    logger.info("QML Arayüzü başarıyla başlatıldı.")
    return app.exec()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(run_qml_app())

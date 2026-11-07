"""Denetleyici kaydı: QML bağlam adı -> sınıf ve kurulum seçenekleri.

Yeni denetleyici yalnızca buraya bir satır ekler (`app.py` değişmez). `AUTOSTART`, `create_controllers`'a verilen
`autostart` bayrağının (testlerde False) iletileceğini belirtir. Denetleyiciler arası sinyal bağlantıları
`app.wire_controllers` içindedir.
"""
from __future__ import annotations

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
from src.ui_qml.controllers.split_events_controller import SplitEventsController
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
from src.ui_qml.controllers.startup_jobs_controller import StartupJobsController
from src.ui_qml.controllers.golden_cross_controller import GoldenCrossController
from src.ui_qml.controllers.risk_profile_controller import RiskProfileController

AUTOSTART = object()

CONTROLLERS = (
    ("shellController", ShellController, {}),
    ("chartController", ChartController, {}),
    ("dashboardController", DashboardController, {}),
    ("myPortfolioController", MyPortfolioController, {}),
    ("assetsController", AssetsController, {"autostart": AUTOSTART}),
    ("watchlistController", WatchlistController, {}),
    ("stock360Controller", Stock360Controller, {}),
    ("portfolioController", ModelPortfolioController, {}),
    ("comparisonController", ComparisonController, {}),
    ("screenerController", ScreenerController, {}),
    ("planningController", PlanningController, {}),
    ("strategyBacktestController", StrategyBacktestController, {}),
    ("marketSyncController", MarketSyncController, {}),
    ("optimizationController", OptimizationController, {}),
    ("aiAdvisorController", AiAdvisorController, {}),
    ("settingsController", SettingsController, {}),
    ("stockDetailController", StockDetailController, {}),
    ("corporateActionController", CorporateActionController, {}),
    ("splitEventsController", SplitEventsController, {}),
    ("dividendController", DividendController, {}),
    ("priceDataController", PriceDataController, {}),
    ("startupJobsController", StartupJobsController, {"autostart": False}),
    ("goldenCrossController", GoldenCrossController, {}),
    ("riskProfileController", RiskProfileController, {}),
    ("marketAdjustmentController", MarketAdjustmentController, {}),
    ("systemController", SystemController, {}),
    ("marketTickerController", MarketTickerController, {}),
    ("newsController", NewsController, {"autostart": AUTOSTART}),
    ("newsSettingsController", NewsSettingsController, {}),
    ("feeSettingsController", FeeSettingsController, {}),
    ("cashPoolController", CashPoolController, {}),
    ("modelAnalysisController", ModelAnalysisController, {}),
)

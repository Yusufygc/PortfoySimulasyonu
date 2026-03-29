# src/application/container.py

from config.settings_loader import load_settings
from src.infrastructure.db.mysql_connection import MySQLConnectionProvider
from src.infrastructure.db.portfolio_repository import MySQLPortfolioRepository
from src.infrastructure.db.price_repository import MySQLPriceRepository
from src.infrastructure.db.stock_repository import MySQLStockRepository
from src.infrastructure.db.watchlist_repository import MySQLWatchlistRepository
from src.infrastructure.db.model_portfolio_repository import MySQLModelPortfolioRepository
from src.infrastructure.db.planning_repository import MySQLPlanningRepository
from src.infrastructure.db.risk_profile_repository import MySQLRiskProfileRepository
from src.infrastructure.market_data.yfinance_client import YFinanceMarketDataClient

from src.application.services.portfolio_service import PortfolioService
from src.application.services.price_update_service import PriceUpdateService
from src.application.services.return_calc_service import ReturnCalcService
from src.application.services.portfolio_update_coordinator import PortfolioUpdateCoordinator
from src.application.services.portfolio_reset_service import PortfolioResetService
from src.application.services.excel_export_service import ExcelExportService
from src.application.services.watchlist_service import WatchlistService
from src.application.services.model_portfolio_service import ModelPortfolioService
from src.application.services.optimization_service import OptimizationService
from src.application.services.planning_service import PlanningService
from src.application.services.risk_profile_service import RiskProfileService
from src.application.services.backfill_service import BackfillService


class AppContainer:
    """
    Dependency Injection Konteyneri.
    Uygulamanın ihtiyaç duyduğu tüm repo ve servisleri tek bir noktada başlatıp tutar.
    Sayfalar ve bileşenler, ihtiyaç duydukları servislere doğrudan bu konteyner üzerinden erişir.
    """
    def __init__(self):
        # 1) DB config & connection pool
        self.db_config = load_settings()
        self.conn_provider = MySQLConnectionProvider(self.db_config)

        # 2) Repositories
        self.portfolio_repo = MySQLPortfolioRepository(self.conn_provider)
        self.price_repo = MySQLPriceRepository(self.conn_provider)
        self.stock_repo = MySQLStockRepository(self.conn_provider)
        self.watchlist_repo = MySQLWatchlistRepository(self.conn_provider)
        self.model_portfolio_repo = MySQLModelPortfolioRepository(self.conn_provider)
        self.planning_repo = MySQLPlanningRepository(self.conn_provider)
        self.risk_profile_repo = MySQLRiskProfileRepository(self.conn_provider)

        # 3) Market data client
        self.market_client = YFinanceMarketDataClient()

        # 4) Services
        self.portfolio_service = PortfolioService(self.portfolio_repo, self.price_repo)
        self.price_update_service = PriceUpdateService(self.price_repo, self.market_client)
        self.return_calc_service = ReturnCalcService(self.portfolio_repo, self.price_repo)
        self.reset_service = PortfolioResetService(self.portfolio_repo, self.price_repo, self.stock_repo)
        
        self.excel_export_service = ExcelExportService(
            portfolio_repo=self.portfolio_repo,
            price_repo=self.price_repo,
            stock_repo=self.stock_repo,
            market_data_client=self.market_client,
        )
        self.watchlist_service = WatchlistService(
            watchlist_repo=self.watchlist_repo,
            stock_repo=self.stock_repo,
        )
        self.model_portfolio_service = ModelPortfolioService(
            model_portfolio_repo=self.model_portfolio_repo,
            stock_repo=self.stock_repo,
        )
        self.optimization_service = OptimizationService(
            portfolio_service=self.portfolio_service,
            model_portfolio_service=self.model_portfolio_service,
            stock_repo=self.stock_repo,
        )
        self.planning_service = PlanningService(
            planning_repo=self.planning_repo,
        )
        self.risk_profile_service = RiskProfileService(
            risk_profile_repo=self.risk_profile_repo,
        )
        self.backfill_service = BackfillService(
            stock_repo=self.stock_repo,
            price_repo=self.price_repo,
        )
        
        # 5) Coordinator
        self.update_coordinator = PortfolioUpdateCoordinator(
            portfolio_repo=self.portfolio_repo,
            stock_repo=self.stock_repo,
            price_update_service=self.price_update_service,
            return_calc_service=self.return_calc_service,
        )

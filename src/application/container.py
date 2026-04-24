# src/application/container.py

from config.settings_loader import load_settings
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.repositories.sa_portfolio_repository import SQLAlchemyPortfolioRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_price_repository import SQLAlchemyPriceRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_stock_repository import SQLAlchemyStockRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_watchlist_repository import SQLAlchemyWatchlistRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_model_portfolio_repository import SQLAlchemyModelPortfolioRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_planning_repository import SQLAlchemyPlanningRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_risk_profile_repository import SQLAlchemyRiskProfileRepository
from src.infrastructure.market_data.yfinance_client import YFinanceMarketDataClient

from src.application.services.portfolio.portfolio_service import PortfolioService
from src.application.services.portfolio.price_update_service import PriceUpdateService
from src.application.services.analysis.return_calc_service import ReturnCalcService
from src.application.services.analysis.analysis_service import AnalysisService
from src.application.services.portfolio.portfolio_update_coordinator import PortfolioUpdateCoordinator
from src.application.services.portfolio.portfolio_reset_service import PortfolioResetService
from src.application.services.reporting.excel_export_service import ExcelExportService
from src.application.services.watchlist.watchlist_service import WatchlistService
from src.application.services.planning.model_portfolio_service import ModelPortfolioService
from src.application.services.planning.optimization_service import OptimizationService
from src.application.services.planning.planning_service import PlanningService
from src.application.services.planning.risk_profile_service import RiskProfileService
from src.application.services.simulation.backfill_service import BackfillService
from src.application.services.simulation.history_simulation_service import HistorySimulationService
from src.application.services.reporting.excel_formatter import ExcelFormatter
from src.application.services.reporting.excel_report_builder import ExcelReportBuilder

class AppContainer:
    """
    Dependency Injection Konteyneri.
    Uygulamanın ihtiyaç duyduğu tüm repo ve servisleri tek bir noktada başlatıp tutar.
    SQLAlchemy sürümüne güncellenmiştir.
    """
    def __init__(self):
        # 0) Event Bus
        from src.application.events.event_bus import GlobalEventBus
        self.event_bus = GlobalEventBus()
        
        # 1) DB config & SQLAlchemy Engine
        self.db_config = load_settings()
        self.conn_provider = SQLAlchemyEngineProvider(self.db_config)

        # 2) Dependencies (ORM Based Repositories)
        self.portfolio_repo = SQLAlchemyPortfolioRepository(self.conn_provider)
        self.price_repo = SQLAlchemyPriceRepository(self.conn_provider)
        self.stock_repo = SQLAlchemyStockRepository(self.conn_provider)
        self.watchlist_repo = SQLAlchemyWatchlistRepository(self.conn_provider)
        self.model_portfolio_repo = SQLAlchemyModelPortfolioRepository(self.conn_provider)
        self.planning_repo = SQLAlchemyPlanningRepository(self.conn_provider)
        self.risk_profile_repo = SQLAlchemyRiskProfileRepository(self.conn_provider)

        # 3) Market data client
        self.market_client = YFinanceMarketDataClient()

        # 4) Services
        self.portfolio_service = PortfolioService(self.portfolio_repo, self.price_repo)
        self.price_update_service = PriceUpdateService(self.price_repo, self.market_client)
        self.return_calc_service = ReturnCalcService(self.portfolio_repo, self.price_repo)
        self.model_portfolio_service = ModelPortfolioService(
            model_portfolio_repo=self.model_portfolio_repo,
            stock_repo=self.stock_repo,
        )
        self.analysis_service = AnalysisService(
            portfolio_repo=self.portfolio_repo,
            price_repo=self.price_repo,
            stock_repo=self.stock_repo,
            market_data_client=self.market_client,
            model_portfolio_service=self.model_portfolio_service,
        )
        self.reset_service = PortfolioResetService(self.portfolio_repo, self.price_repo, self.stock_repo)
        
        self.history_simulation_service = HistorySimulationService(
            portfolio_repo=self.portfolio_repo,
            price_repo=self.price_repo,
            stock_repo=self.stock_repo,
            market_data_client=self.market_client,
        )
        self.excel_formatter = ExcelFormatter()
        self.excel_report_builder = ExcelReportBuilder(formatter=self.excel_formatter)
        
        self.excel_export_service = ExcelExportService(
            simulation_service=self.history_simulation_service,
            report_builder=self.excel_report_builder,
        )

        self.watchlist_service = WatchlistService(
            watchlist_repo=self.watchlist_repo,
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
            event_bus=self.event_bus,
        )

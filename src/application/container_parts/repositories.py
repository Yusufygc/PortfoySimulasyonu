from __future__ import annotations

from dataclasses import dataclass

from src.infrastructure.db.sqlalchemy.repositories.sa_asset_price_repository import SQLAlchemyAssetPriceRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_asset_repository import SQLAlchemyAssetRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_asset_trade_repository import SQLAlchemyAssetTradeRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_cash_movement_repository import SQLAlchemyCashMovementRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_corporate_action_candidate_repository import (
    SQLAlchemyCorporateActionCandidateRepository,
)
from src.infrastructure.db.sqlalchemy.repositories.sa_corporate_action_repository import SQLAlchemyCorporateActionRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_fx_rate_repository import SQLAlchemyFxRateRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_latest_price_repository import SQLAlchemyLatestPriceRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_news_source_repository import SQLAlchemyNewsSourceRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_model_portfolio_repository import SQLAlchemyModelPortfolioRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_planning_repository import SQLAlchemyPlanningRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_portfolio_maintenance_repository import SQLAlchemyPortfolioMaintenanceRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_portfolio_repository import SQLAlchemyPortfolioRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_price_repository import SQLAlchemyPriceRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_risk_profile_repository import SQLAlchemyRiskProfileRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_golden_cross_repository import SQLAlchemyGoldenCrossRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_shareholder_repository import SQLAlchemyKapShareholderRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_stock_repository import SQLAlchemyStockRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_trade_adjustment_repository import SQLAlchemyTradeAdjustmentRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_watchlist_repository import SQLAlchemyWatchlistRepository
from src.infrastructure.market_data.duckdb_corporate_action_store import DuckDBCorporateActionStore
from src.infrastructure.market_data.duckdb_market_history_repo import DuckDBMarketHistoryRepository



@dataclass(frozen=True)
class RepositorySet:
    portfolio_repo: SQLAlchemyPortfolioRepository
    price_repo: SQLAlchemyPriceRepository
    market_history_repo: DuckDBMarketHistoryRepository  # DuckDB (OLAP), salt okunur
    market_action_repo: DuckDBCorporateActionStore  # DuckDB ticker bazlı kurumsal aksiyon/faktör deposu
    latest_price_repo: SQLAlchemyLatestPriceRepository
    cash_movement_repo: SQLAlchemyCashMovementRepository
    portfolio_maintenance_repo: SQLAlchemyPortfolioMaintenanceRepository
    stock_repo: SQLAlchemyStockRepository
    watchlist_repo: SQLAlchemyWatchlistRepository
    model_portfolio_repo: SQLAlchemyModelPortfolioRepository
    planning_repo: SQLAlchemyPlanningRepository
    risk_profile_repo: SQLAlchemyRiskProfileRepository
    corporate_action_repo: SQLAlchemyCorporateActionRepository
    corporate_action_candidate_repo: SQLAlchemyCorporateActionCandidateRepository
    trade_adjustment_repo: SQLAlchemyTradeAdjustmentRepository
    kap_shareholder_repo: SQLAlchemyKapShareholderRepository
    golden_cross_repo: SQLAlchemyGoldenCrossRepository
    asset_repo: SQLAlchemyAssetRepository  # BIST dışı varlık defteri (Portföyüm)
    asset_trade_repo: SQLAlchemyAssetTradeRepository
    asset_price_repo: SQLAlchemyAssetPriceRepository
    fx_rate_repo: SQLAlchemyFxRateRepository
    news_source_repo: SQLAlchemyNewsSourceRepository  # haber kaynağı açık/kapalı tercihleri


def build_repositories(conn_provider) -> RepositorySet:
    stock_r = SQLAlchemyStockRepository(conn_provider)
    return RepositorySet(
        portfolio_repo=SQLAlchemyPortfolioRepository(conn_provider),
        price_repo=SQLAlchemyPriceRepository(conn_provider),
        market_history_repo=DuckDBMarketHistoryRepository(),
        market_action_repo=DuckDBCorporateActionStore(),
        latest_price_repo=SQLAlchemyLatestPriceRepository(conn_provider),
        cash_movement_repo=SQLAlchemyCashMovementRepository(conn_provider),
        portfolio_maintenance_repo=SQLAlchemyPortfolioMaintenanceRepository(conn_provider),
        stock_repo=stock_r,
        watchlist_repo=SQLAlchemyWatchlistRepository(conn_provider),
        model_portfolio_repo=SQLAlchemyModelPortfolioRepository(conn_provider),
        planning_repo=SQLAlchemyPlanningRepository(conn_provider),
        risk_profile_repo=SQLAlchemyRiskProfileRepository(conn_provider),
        corporate_action_repo=SQLAlchemyCorporateActionRepository(conn_provider),
        corporate_action_candidate_repo=SQLAlchemyCorporateActionCandidateRepository(conn_provider),
        trade_adjustment_repo=SQLAlchemyTradeAdjustmentRepository(conn_provider),
        kap_shareholder_repo=SQLAlchemyKapShareholderRepository(conn_provider),
        golden_cross_repo=SQLAlchemyGoldenCrossRepository(conn_provider),
        asset_repo=SQLAlchemyAssetRepository(conn_provider),
        asset_trade_repo=SQLAlchemyAssetTradeRepository(conn_provider),
        asset_price_repo=SQLAlchemyAssetPriceRepository(conn_provider),
        fx_rate_repo=SQLAlchemyFxRateRepository(conn_provider),
        news_source_repo=SQLAlchemyNewsSourceRepository(conn_provider),
    )

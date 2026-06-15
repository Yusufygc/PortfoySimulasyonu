from __future__ import annotations

from dataclasses import dataclass

from src.infrastructure.db.sqlalchemy.repositories.sa_cash_movement_repository import SQLAlchemyCashMovementRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_corporate_action_candidate_repository import (
    SQLAlchemyCorporateActionCandidateRepository,
)
from src.infrastructure.db.sqlalchemy.repositories.sa_corporate_action_repository import SQLAlchemyCorporateActionRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_latest_price_repository import SQLAlchemyLatestPriceRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_model_portfolio_repository import SQLAlchemyModelPortfolioRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_planning_repository import SQLAlchemyPlanningRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_portfolio_maintenance_repository import SQLAlchemyPortfolioMaintenanceRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_portfolio_repository import SQLAlchemyPortfolioRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_price_repository import SQLAlchemyPriceRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_risk_profile_repository import SQLAlchemyRiskProfileRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_shareholder_repository import SQLAlchemyKapShareholderRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_stock_repository import SQLAlchemyStockRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_trade_adjustment_repository import SQLAlchemyTradeAdjustmentRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_watchlist_repository import SQLAlchemyWatchlistRepository



@dataclass(frozen=True)
class RepositorySet:
    portfolio_repo: SQLAlchemyPortfolioRepository
    price_repo: SQLAlchemyPriceRepository
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


def build_repositories(conn_provider) -> RepositorySet:
    return RepositorySet(
        portfolio_repo=SQLAlchemyPortfolioRepository(conn_provider),
        price_repo=SQLAlchemyPriceRepository(conn_provider),
        latest_price_repo=SQLAlchemyLatestPriceRepository(conn_provider),
        cash_movement_repo=SQLAlchemyCashMovementRepository(conn_provider),
        portfolio_maintenance_repo=SQLAlchemyPortfolioMaintenanceRepository(conn_provider),
        stock_repo=SQLAlchemyStockRepository(conn_provider),
        watchlist_repo=SQLAlchemyWatchlistRepository(conn_provider),
        model_portfolio_repo=SQLAlchemyModelPortfolioRepository(conn_provider),
        planning_repo=SQLAlchemyPlanningRepository(conn_provider),
        risk_profile_repo=SQLAlchemyRiskProfileRepository(conn_provider),
        corporate_action_repo=SQLAlchemyCorporateActionRepository(conn_provider),
        corporate_action_candidate_repo=SQLAlchemyCorporateActionCandidateRepository(conn_provider),
        trade_adjustment_repo=SQLAlchemyTradeAdjustmentRepository(conn_provider),
        kap_shareholder_repo=SQLAlchemyKapShareholderRepository(conn_provider),
    )

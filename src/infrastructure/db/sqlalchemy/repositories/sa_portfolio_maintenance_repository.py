from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from src.application.services.portfolio.portfolio_maintenance_service import PurgeStockResult
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import (
    ORMCorporateAction,
    ORMDailyPrice,
    ORMModelPortfolioTrade,
    ORMStock,
    ORMTrade,
    ORMWatchlistItem,
)


class SQLAlchemyPortfolioMaintenanceRepository:
    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    def purge_stock_by_ticker(self, ticker: str) -> PurgeStockResult:
        base_ticker = self._normalize_ticker(ticker)
        candidates = {base_ticker, f"{base_ticker}.IS"}
        session = self._provider.get_session()
        try:
            stock_rows = (
                session.query(ORMStock.id)
                .filter(func.upper(ORMStock.ticker).in_(candidates))
                .all()
            )
            stock_ids = tuple(int(row.id) for row in stock_rows)
            if not stock_ids:
                return PurgeStockResult(ticker=base_ticker, stock_ids=())

            deleted_trades = self._delete_by_stock_ids(session, ORMTrade, stock_ids)
            deleted_daily_prices = self._delete_by_stock_ids(session, ORMDailyPrice, stock_ids)
            deleted_watchlist_items = self._delete_by_stock_ids(session, ORMWatchlistItem, stock_ids)
            deleted_model_portfolio_trades = self._delete_by_stock_ids(session, ORMModelPortfolioTrade, stock_ids)
            deleted_corporate_actions = self._delete_by_stock_ids(session, ORMCorporateAction, stock_ids)
            deleted_stocks = (
                session.query(ORMStock)
                .filter(ORMStock.id.in_(stock_ids))
                .delete(synchronize_session=False)
            )
            session.commit()
            return PurgeStockResult(
                ticker=base_ticker,
                stock_ids=stock_ids,
                deleted_trades=deleted_trades,
                deleted_daily_prices=deleted_daily_prices,
                deleted_watchlist_items=deleted_watchlist_items,
                deleted_model_portfolio_trades=deleted_model_portfolio_trades,
                deleted_corporate_actions=deleted_corporate_actions,
                deleted_stocks=deleted_stocks,
            )
        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _delete_by_stock_ids(session, orm_model, stock_ids: tuple[int, ...]) -> int:
        return (
            session.query(orm_model)
            .filter(orm_model.stock_id.in_(stock_ids))
            .delete(synchronize_session=False)
        )

    @staticmethod
    def _normalize_ticker(ticker: str) -> str:
        value = (ticker or "").strip().upper()
        return value[:-3] if value.endswith(".IS") else value

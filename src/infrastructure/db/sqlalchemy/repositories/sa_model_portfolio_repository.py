# src/infrastructure/db/sqlalchemy/repositories/sa_model_portfolio_repository.py

from datetime import date, time
from decimal import Decimal
from typing import List, Optional

from src.domain.models.model_portfolio import ModelPortfolio, ModelPortfolioTrade, ModelTradeSide
from src.domain.ports.repositories.i_model_portfolio_repo import IModelPortfolioRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMModelPortfolio, ORMModelPortfolioTrade

class SQLAlchemyModelPortfolioRepository(IModelPortfolioRepository):
    """
    IModelPortfolioRepository arayüzünün SQLAlchemy tabanlı uygulaması.
    """

    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    # ---------- Mappers ---------- #
    def _to_domain_portfolio(self, orm: ORMModelPortfolio) -> ModelPortfolio:
        initial_cash = orm.initial_cash
        if initial_cash is not None and not isinstance(initial_cash, Decimal):
            initial_cash = Decimal(str(initial_cash))

        return ModelPortfolio(
            id=orm.id,
            name=orm.name,
            description=orm.description,
            initial_cash=initial_cash or Decimal("100000.00"),
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def _to_orm_portfolio(self, domain: ModelPortfolio) -> ORMModelPortfolio:
        return ORMModelPortfolio(
            id=domain.id,
            name=domain.name,
            description=domain.description,
            initial_cash=domain.initial_cash,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
        )

    def _to_domain_trade(self, orm: ORMModelPortfolioTrade) -> ModelPortfolioTrade:
        price_val = orm.price
        if not isinstance(price_val, Decimal):
            price_val = Decimal(str(price_val))

        return ModelPortfolioTrade(
            id=orm.id,
            portfolio_id=orm.portfolio_id,
            stock_id=orm.stock_id,
            trade_date=orm.trade_date,
            trade_time=orm.trade_time,
            side=ModelTradeSide(orm.side.value),
            quantity=orm.quantity,
            price=price_val,
            created_at=orm.created_at,
        )

    def _to_orm_trade(self, domain: ModelPortfolioTrade) -> ORMModelPortfolioTrade:
        return ORMModelPortfolioTrade(
            id=domain.id,
            portfolio_id=domain.portfolio_id,
            stock_id=domain.stock_id,
            trade_date=domain.trade_date,
            trade_time=domain.trade_time,
            side=domain.side.value,
            quantity=domain.quantity,
            price=domain.price,
            created_at=domain.created_at,
        )

    # ---------- ModelPortfolio READ operasyonları ---------- #
    def get_all_model_portfolios(self) -> List[ModelPortfolio]:
        with self._provider.get_session() as session:
            rows = session.query(ORMModelPortfolio).order_by(ORMModelPortfolio.name).all()
            return [self._to_domain_portfolio(r) for r in rows]

    def get_model_portfolio_by_id(self, portfolio_id: int) -> Optional[ModelPortfolio]:
        with self._provider.get_session() as session:
            row = session.query(ORMModelPortfolio).filter_by(id=portfolio_id).first()
            return self._to_domain_portfolio(row) if row else None

    # ---------- ModelPortfolio WRITE operasyonları ---------- #
    def create_model_portfolio(self, portfolio: ModelPortfolio) -> ModelPortfolio:
        with self._provider.get_session() as session:
            orm_obj = self._to_orm_portfolio(portfolio)
            session.add(orm_obj)
            session.commit()
            session.refresh(orm_obj)
            return self._to_domain_portfolio(orm_obj)

    def update_model_portfolio(self, portfolio: ModelPortfolio) -> None:
        if portfolio.id is None:
            raise ValueError("Portfolio id is required for update")
        with self._provider.get_session() as session:
            orm_obj = session.query(ORMModelPortfolio).filter_by(id=portfolio.id).first()
            if orm_obj:
                orm_obj.name = portfolio.name
                orm_obj.description = portfolio.description
                orm_obj.initial_cash = portfolio.initial_cash
                session.commit()

    def delete_model_portfolio(self, portfolio_id: int) -> None:
        with self._provider.get_session() as session:
            orm_obj = session.query(ORMModelPortfolio).filter_by(id=portfolio_id).first()
            if orm_obj:
                session.delete(orm_obj)
                session.commit()

    def delete_all_model_portfolios(self) -> None:
        with self._provider.get_session() as session:
            session.query(ORMModelPortfolioTrade).delete()
            session.query(ORMModelPortfolio).delete()
            session.commit()

    # ---------- ModelPortfolioTrade READ operasyonları ---------- #
    def get_trades_by_portfolio_id(self, portfolio_id: int) -> List[ModelPortfolioTrade]:
        with self._provider.get_session() as session:
            rows = session.query(ORMModelPortfolioTrade)\
                .filter_by(portfolio_id=portfolio_id)\
                .order_by(ORMModelPortfolioTrade.trade_date, ORMModelPortfolioTrade.trade_time, ORMModelPortfolioTrade.id)\
                .all()
            return [self._to_domain_trade(r) for r in rows]

    def count_trades_by_portfolio_id(self, portfolio_id: int) -> int:
        with self._provider.get_session() as session:
            return session.query(ORMModelPortfolioTrade).filter_by(portfolio_id=portfolio_id).count()

    def get_trade_by_id(self, trade_id: int) -> Optional[ModelPortfolioTrade]:
        with self._provider.get_session() as session:
            row = session.query(ORMModelPortfolioTrade).filter_by(id=trade_id).first()
            return self._to_domain_trade(row) if row else None

    # ---------- ModelPortfolioTrade WRITE operasyonları ---------- #
    def insert_trade(self, trade: ModelPortfolioTrade) -> ModelPortfolioTrade:
        with self._provider.get_session() as session:
            orm_obj = self._to_orm_trade(trade)
            session.add(orm_obj)
            session.commit()
            session.refresh(orm_obj)
            return self._to_domain_trade(orm_obj)

    def delete_trade(self, trade_id: int) -> None:
        with self._provider.get_session() as session:
            orm_obj = session.query(ORMModelPortfolioTrade).filter_by(id=trade_id).first()
            if orm_obj:
                session.delete(orm_obj)
                session.commit()

    def delete_all_trades_by_portfolio_id(self, portfolio_id: int) -> None:
        with self._provider.get_session() as session:
            session.query(ORMModelPortfolioTrade).filter_by(portfolio_id=portfolio_id).delete()
            session.commit()

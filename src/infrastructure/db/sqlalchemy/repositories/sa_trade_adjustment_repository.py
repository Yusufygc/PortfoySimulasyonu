# src/infrastructure/db/sqlalchemy/repositories/sa_trade_adjustment_repository.py

from datetime import datetime
from decimal import Decimal
from typing import List

from src.domain.models.trade_adjustment import TradeAdjustment
from src.domain.ports.repositories.i_trade_adjustment_repo import ITradeAdjustmentRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMTradeAdjustment
from src.infrastructure.db.sqlalchemy.repositories._transaction import commit_refresh_or_rollback

class SQLAlchemyTradeAdjustmentRepository(ITradeAdjustmentRepository):
    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    def _to_domain(self, orm: ORMTradeAdjustment) -> TradeAdjustment:
        factor_dec = orm.factor
        if not isinstance(factor_dec, Decimal):
            factor_dec = Decimal(str(factor_dec))
        pre_price_dec = orm.pre_price
        if not isinstance(pre_price_dec, Decimal):
            pre_price_dec = Decimal(str(pre_price_dec))
        post_price_dec = orm.post_price
        if not isinstance(post_price_dec, Decimal):
            post_price_dec = Decimal(str(post_price_dec))

        return TradeAdjustment(
            id=orm.id,
            trade_id=orm.trade_id,
            corporate_action_id=orm.corporate_action_id,
            factor=factor_dec,
            pre_quantity=orm.pre_quantity,
            post_quantity=orm.post_quantity,
            pre_price=pre_price_dec,
            post_price=post_price_dec,
            applied_at=orm.applied_at
        )

    def _to_orm(self, domain: TradeAdjustment) -> ORMTradeAdjustment:
        return ORMTradeAdjustment(
            id=domain.id,
            trade_id=domain.trade_id,
            corporate_action_id=domain.corporate_action_id,
            factor=domain.factor,
            pre_quantity=domain.pre_quantity,
            post_quantity=domain.post_quantity,
            pre_price=domain.pre_price,
            post_price=domain.post_price,
            applied_at=domain.applied_at
        )

    def insert(self, adjustment: TradeAdjustment) -> TradeAdjustment:
        with self._provider.get_session() as session:
            orm_obj = self._to_orm(adjustment)
            session.add(orm_obj)
            commit_refresh_or_rollback(session, orm_obj)
            return self._to_domain(orm_obj)

    def get_by_trade_id(self, trade_id: int) -> List[TradeAdjustment]:
        with self._provider.get_session() as session:
            rows = session.query(ORMTradeAdjustment).filter_by(trade_id=trade_id).order_by(ORMTradeAdjustment.applied_at.desc()).all()
            return [self._to_domain(r) for r in rows]

    def get_by_corporate_action_id(self, corporate_action_id: int) -> List[TradeAdjustment]:
        with self._provider.get_session() as session:
            rows = session.query(ORMTradeAdjustment).filter_by(corporate_action_id=corporate_action_id).order_by(ORMTradeAdjustment.applied_at.desc()).all()
            return [self._to_domain(r) for r in rows]

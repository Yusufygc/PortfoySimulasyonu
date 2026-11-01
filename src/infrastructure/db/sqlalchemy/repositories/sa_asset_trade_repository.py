from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from src.domain.models.asset_trade import AssetTrade
from src.domain.models.trade import TradeSide
from src.domain.ports.repositories.i_asset_trade_repo import IAssetTradeRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMAssetTrade
from src.infrastructure.db.sqlalchemy.repositories._transaction import commit_or_rollback, commit_refresh_or_rollback


def _decimal(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _to_domain(orm: ORMAssetTrade) -> AssetTrade:
    return AssetTrade(
        id=orm.id,
        asset_id=orm.asset_id,
        trade_date=orm.trade_date,
        trade_time=orm.trade_time,
        side=TradeSide(orm.side.value),
        quantity=_decimal(orm.quantity),
        price=_decimal(orm.price),
        fx_rate_to_try=_decimal(orm.fx_rate_to_try),
        note=orm.note,
        fee=_decimal(orm.fee) if orm.fee is not None else Decimal("0"),
    )


def _to_orm(trade: AssetTrade) -> ORMAssetTrade:
    return ORMAssetTrade(
        id=trade.id,
        asset_id=trade.asset_id,
        trade_date=trade.trade_date,
        trade_time=trade.trade_time,
        side=trade.side.value,
        quantity=trade.quantity,
        price=trade.price,
        fx_rate_to_try=trade.fx_rate_to_try,
        note=trade.note,
        fee=trade.fee,
    )


class SQLAlchemyAssetTradeRepository(IAssetTradeRepository):
    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    def add_trade(self, trade: AssetTrade) -> AssetTrade:
        with self._provider.get_session() as session:
            orm_obj = _to_orm(trade)
            session.add(orm_obj)
            commit_refresh_or_rollback(session, orm_obj)
            return _to_domain(orm_obj)

    def get_trade(self, trade_id: int) -> Optional[AssetTrade]:
        with self._provider.get_session() as session:
            row = session.get(ORMAssetTrade, trade_id)
            return _to_domain(row) if row is not None else None

    def list_trades(self, asset_id: Optional[int] = None) -> List[AssetTrade]:
        with self._provider.get_session() as session:
            query = session.query(ORMAssetTrade)
            if asset_id is not None:
                query = query.filter(ORMAssetTrade.asset_id == asset_id)
            rows = query.order_by(ORMAssetTrade.trade_date, ORMAssetTrade.trade_time, ORMAssetTrade.id).all()
            return [_to_domain(row) for row in rows]

    def delete_trade(self, trade_id: int) -> None:
        with self._provider.get_session() as session:
            session.query(ORMAssetTrade).filter(ORMAssetTrade.id == trade_id).delete()
            commit_or_rollback(session)

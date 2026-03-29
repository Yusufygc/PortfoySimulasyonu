# src/infrastructure/db/sqlalchemy/repositories/sa_portfolio_repository.py

from datetime import date
from typing import Iterable, List, Optional, Sequence
from src.domain.models.trade import Trade, TradeSide
from src.domain.services_interfaces.i_portfolio_repo import IPortfolioRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMTrade

class SQLAlchemyPortfolioRepository(IPortfolioRepository):
    """
    IPortfolioRepository arayüzünün SQLAlchemy tabanlı uygulaması.
    """

    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    # ---------- Mapper ---------- #
    def _to_domain(self, orm: ORMTrade) -> Trade:
        return Trade(
            id=orm.id,
            stock_id=orm.stock_id,
            trade_date=orm.trade_date,
            trade_time=orm.trade_time,
            side=TradeSide(orm.side.value),  # Enum'dan string eşleştirmesi
            quantity=orm.quantity,
            price=orm.price,
        )

    def _to_orm(self, domain: Trade) -> ORMTrade:
        return ORMTrade(
            id=domain.id,
            stock_id=domain.stock_id,
            trade_date=domain.trade_date,
            trade_time=domain.trade_time,
            side=domain.side.value,
            quantity=domain.quantity,
            price=domain.price,
        )

    # ---------- READ ---------- #
    def get_all_trades(self) -> List[Trade]:
        with self._provider.get_session() as session:
            rows = session.query(ORMTrade).order_by(ORMTrade.trade_date, ORMTrade.trade_time, ORMTrade.id).all()
            return [self._to_domain(r) for r in rows]

    def get_trades_by_stock(self, stock_id: int) -> List[Trade]:
        with self._provider.get_session() as session:
            rows = session.query(ORMTrade).filter_by(stock_id=stock_id).order_by(ORMTrade.trade_date, ORMTrade.trade_time, ORMTrade.id).all()
            return [self._to_domain(r) for r in rows]

    def get_trades_by_date_range(self, start_date: date, end_date: date) -> List[Trade]:
        with self._provider.get_session() as session:
            rows = session.query(ORMTrade)\
                .filter(ORMTrade.trade_date >= start_date)\
                .filter(ORMTrade.trade_date <= end_date)\
                .order_by(ORMTrade.trade_date, ORMTrade.trade_time, ORMTrade.id).all()
            return [self._to_domain(r) for r in rows]

    def get_trade_by_id(self, trade_id: int) -> Optional[Trade]:
        with self._provider.get_session() as session:
            row = session.query(ORMTrade).filter_by(id=trade_id).first()
            return self._to_domain(row) if row else None

    def get_all_stock_ids_in_portfolio(self) -> Sequence[int]:
        with self._provider.get_session() as session:
            # Sadece distinct stock_id leri çeker
            rows = session.query(ORMTrade.stock_id).distinct().all()
            return [r.stock_id for r in rows]

    # ---------- WRITE ---------- #
    def insert_trade(self, trade: Trade) -> Trade:
        with self._provider.get_session() as session:
            orm_obj = self._to_orm(trade)
            session.add(orm_obj)
            session.commit()
            session.refresh(orm_obj)
            return self._to_domain(orm_obj)

    def insert_trades_bulk(self, trades: Iterable[Trade]) -> None:
        trades_list = list(trades)
        if not trades_list:
            return
        with self._provider.get_session() as session:
            orm_objs = [self._to_orm(t) for t in trades_list]
            session.add_all(orm_objs)
            session.commit()

    def update_trade(self, trade: Trade) -> None:
        if trade.id is None:
            raise ValueError("Trade id is required for update")
        with self._provider.get_session() as session:
            orm_obj = session.query(ORMTrade).filter_by(id=trade.id).first()
            if orm_obj:
                orm_obj.stock_id = trade.stock_id
                orm_obj.trade_date = trade.trade_date
                orm_obj.trade_time = trade.trade_time
                orm_obj.side = trade.side.value
                orm_obj.quantity = trade.quantity
                orm_obj.price = trade.price
                session.commit()

    def delete_trade(self, trade_id: int) -> None:
        with self._provider.get_session() as session:
            orm_obj = session.query(ORMTrade).filter_by(id=trade_id).first()
            if orm_obj:
                session.delete(orm_obj)
                session.commit()

    def delete_all_trades(self) -> None:
        with self._provider.get_session() as session:
            session.query(ORMTrade).delete()
            session.commit()

    def get_first_trade_date(self) -> Optional[date]:
        with self._provider.get_session() as session:
            row = session.query(ORMTrade.trade_date).order_by(ORMTrade.trade_date.asc()).first()
            return row.trade_date if row else None

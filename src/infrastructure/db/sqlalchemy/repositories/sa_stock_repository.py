# src/infrastructure/db/sqlalchemy/repositories/sa_stock_repository.py

from typing import Dict, Iterable, List, Optional, Sequence
from src.domain.models.stock import Stock
from src.domain.services_interfaces.i_stock_repo import IStockRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMStock

class SQLAlchemyStockRepository(IStockRepository):
    """
    IStockRepository arayüzünün SQLAlchemy tabanlı uygulaması.
    """

    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    # ---------- Row → Domain Mapper ---------- #
    def _to_domain(self, orm: ORMStock) -> Stock:
        return Stock(
            id=orm.id,
            ticker=orm.ticker,
            name=orm.name,
            currency_code=orm.currency_code,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    # ---------- Domain → Row Mapper ---------- #
    def _to_orm(self, domain: Stock) -> ORMStock:
        return ORMStock(
            id=domain.id, # Insert için None gelecektir
            ticker=domain.ticker,
            name=domain.name,
            currency_code=domain.currency_code,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
        )

    # ---------- READ operasyonları ---------- #
    def get_all_stocks(self) -> List[Stock]:
        with self._provider.get_session() as session:
            rows = session.query(ORMStock).order_by(ORMStock.ticker).all()
            return [self._to_domain(r) for r in rows]

    def get_stock_by_id(self, stock_id: int) -> Optional[Stock]:
        with self._provider.get_session() as session:
            row = session.query(ORMStock).filter_by(id=stock_id).first()
            if row is None:
                return None
            return self._to_domain(row)

    def get_stock_by_ticker(self, ticker: str) -> Optional[Stock]:
        with self._provider.get_session() as session:
            row = session.query(ORMStock).filter_by(ticker=ticker).first()
            if row is None:
                return None
            return self._to_domain(row)

    def get_stocks_by_ids(self, stock_ids: Sequence[int]) -> List[Stock]:
        if not stock_ids:
            return []
        with self._provider.get_session() as session:
            rows = session.query(ORMStock).filter(ORMStock.id.in_(stock_ids)).order_by(ORMStock.ticker).all()
            return [self._to_domain(r) for r in rows]

    def get_ticker_map_for_stock_ids(self, stock_ids: Sequence[int]) -> Dict[int, str]:
        if not stock_ids:
            return {}
        with self._provider.get_session() as session:
            # Query specific columns for performance
            rows = session.query(ORMStock.id, ORMStock.ticker).filter(ORMStock.id.in_(stock_ids)).all()
            result: Dict[int, str] = {}
            for row in rows:
                result[row.id] = row.ticker
            return result

    # ---------- WRITE operasyonları ---------- #
    def insert_stock(self, stock: Stock) -> Stock:
        with self._provider.get_session() as session:
            orm_obj = self._to_orm(stock)
            session.add(orm_obj)
            session.commit()
            session.refresh(orm_obj) # id ve created_at değerlerini almak için
            return self._to_domain(orm_obj)

    def insert_stocks_bulk(self, stocks: Iterable[Stock]) -> None:
        stocks_list = list(stocks)
        if not stocks_list:
            return
        with self._provider.get_session() as session:
            orm_objs = [self._to_orm(s) for s in stocks_list]
            session.add_all(orm_objs)
            session.commit()

    def update_stock(self, stock: Stock) -> None:
        if stock.id is None:
            raise ValueError("Stock id is required for update")
            
        with self._provider.get_session() as session:
            orm_obj = session.query(ORMStock).filter_by(id=stock.id).first()
            if orm_obj:
                orm_obj.ticker = stock.ticker
                orm_obj.name = stock.name
                orm_obj.currency_code = stock.currency_code
                # created_at and updated_at handled by DB / server_default / onupdate
                session.commit()

    def delete_stock(self, stock_id: int) -> None:
        with self._provider.get_session() as session:
            orm_obj = session.query(ORMStock).filter_by(id=stock_id).first()
            if orm_obj:
                session.delete(orm_obj)
                session.commit()

    def delete_all_stocks(self) -> None:
        """
        Not: FK'ler nedeniyle önce child tablolar temizlenmiş olmalı.
        """
        with self._provider.get_session() as session:
            session.query(ORMStock).delete()
            session.commit()

# src/infrastructure/db/sqlalchemy/repositories/sa_price_repository.py

from datetime import date
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Sequence

from sqlalchemy.dialects.mysql import insert
from src.domain.models.daily_price import DailyPrice
from src.domain.services_interfaces.i_price_repo import IPriceRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMDailyPrice

class SQLAlchemyPriceRepository(IPriceRepository):
    """
    IPriceRepository arayüzünün SQLAlchemy tabanlı uygulaması.
    """

    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    # ---------- Mapper ---------- #
    def _to_domain(self, orm: ORMDailyPrice) -> DailyPrice:
        close_p = orm.close_price
        if not isinstance(close_p, Decimal):
            close_p = Decimal(str(close_p))
            
        return DailyPrice(
            id=orm.id,
            stock_id=orm.stock_id,
            price_date=orm.price_date,
            close_price=close_p,
            currency_code=orm.currency_code,
            source=orm.source,
        )

    # ---------- READ ---------- #
    def get_price_for_date(self, stock_id: int, price_date: date) -> Optional[DailyPrice]:
        with self._provider.get_session() as session:
            row = session.query(ORMDailyPrice).filter_by(stock_id=stock_id, price_date=price_date).first()
            return self._to_domain(row) if row else None

    def get_prices_for_date(self, price_date: date) -> Dict[int, Decimal]:
        with self._provider.get_session() as session:
            rows = session.query(ORMDailyPrice.stock_id, ORMDailyPrice.close_price).filter_by(price_date=price_date).all()
            result = {}
            for r in rows:
                val = r.close_price
                if not isinstance(val, Decimal):
                    val = Decimal(str(val))
                result[r.stock_id] = val
            return result

    def get_last_price_before(self, stock_id: int, price_date: date) -> Optional[DailyPrice]:
        with self._provider.get_session() as session:
            row = session.query(ORMDailyPrice)\
                .filter(ORMDailyPrice.stock_id == stock_id)\
                .filter(ORMDailyPrice.price_date <= price_date)\
                .order_by(ORMDailyPrice.price_date.desc())\
                .first()
            return self._to_domain(row) if row else None

    def get_price_series(self, stock_id: int, start_date: date, end_date: date) -> List[DailyPrice]:
        with self._provider.get_session() as session:
            rows = session.query(ORMDailyPrice)\
                .filter(ORMDailyPrice.stock_id == stock_id)\
                .filter(ORMDailyPrice.price_date >= start_date)\
                .filter(ORMDailyPrice.price_date <= end_date)\
                .order_by(ORMDailyPrice.price_date.asc()).all()
            return [self._to_domain(r) for r in rows]

    def get_portfolio_value_series(self, stock_ids: Sequence[int], start_date: date, end_date: date) -> Dict[date, Dict[int, Decimal]]:
        if not stock_ids:
            return {}
        with self._provider.get_session() as session:
            rows = session.query(ORMDailyPrice.stock_id, ORMDailyPrice.price_date, ORMDailyPrice.close_price)\
                .filter(ORMDailyPrice.stock_id.in_(stock_ids))\
                .filter(ORMDailyPrice.price_date >= start_date)\
                .filter(ORMDailyPrice.price_date <= end_date)\
                .order_by(ORMDailyPrice.price_date.asc(), ORMDailyPrice.stock_id.asc()).all()
            
            result: Dict[date, Dict[int, Decimal]] = {}
            for r in rows:
                val = r.close_price
                if not isinstance(val, Decimal):
                    val = Decimal(str(val))
                if r.price_date not in result:
                    result[r.price_date] = {}
                result[r.price_date][r.stock_id] = val
            return result

    # ---------- WRITE (UPSERT) ---------- #
    def upsert_daily_price(self, daily_price: DailyPrice) -> DailyPrice:
        with self._provider.get_session() as session:
            stmt = insert(ORMDailyPrice).values(
                stock_id=daily_price.stock_id,
                price_date=daily_price.price_date,
                close_price=daily_price.close_price,
                currency_code=daily_price.currency_code,
                source=daily_price.source
            )
            stmt = stmt.on_duplicate_key_update(
                close_price=stmt.inserted.close_price,
                currency_code=stmt.inserted.currency_code,
                source=stmt.inserted.source
            )
            result = session.execute(stmt)
            session.commit()
            
            # last inserted id
            inserted_id = result.lastrowid
            return DailyPrice(
                id=inserted_id if inserted_id else daily_price.id,
                stock_id=daily_price.stock_id,
                price_date=daily_price.price_date,
                close_price=daily_price.close_price,
                currency_code=daily_price.currency_code,
                source=daily_price.source
            )

    def upsert_daily_prices_bulk(self, prices: Iterable[DailyPrice]) -> None:
        prices_list = list(prices)
        if not prices_list:
            return
        
        values = [
            {
                "stock_id": p.stock_id,
                "price_date": p.price_date,
                "close_price": p.close_price,
                "currency_code": p.currency_code,
                "source": p.source
            } for p in prices_list
        ]
        
        with self._provider.get_session() as session:
            stmt = insert(ORMDailyPrice).values(values)
            stmt = stmt.on_duplicate_key_update(
                close_price=stmt.inserted.close_price,
                currency_code=stmt.inserted.currency_code,
                source=stmt.inserted.source
            )
            session.execute(stmt)
            session.commit()

    def delete_all_prices(self) -> None:
        with self._provider.get_session() as session:
            session.query(ORMDailyPrice).delete()
            session.commit()

    def delete_prices_in_range(self, start_date: date, end_date: date) -> int:
        with self._provider.get_session() as session:
            deleted_count = session.query(ORMDailyPrice)\
                .filter(ORMDailyPrice.price_date >= start_date)\
                .filter(ORMDailyPrice.price_date <= end_date)\
                .delete()
            session.commit()
            return deleted_count

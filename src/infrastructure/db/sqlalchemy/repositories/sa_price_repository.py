# src/infrastructure/db/sqlalchemy/repositories/sa_price_repository.py

from datetime import date
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Sequence, Set

from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy import func
from src.domain.models.daily_price import DailyPrice
from src.domain.ports.repositories.i_price_repo import IPriceRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMDailyPrice
from src.infrastructure.db.sqlalchemy.repositories._transaction import commit_or_rollback

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
            open_price=self._to_optional_decimal(orm.open_price),
            high_price=self._to_optional_decimal(orm.high_price),
            low_price=self._to_optional_decimal(orm.low_price),
            volume=orm.volume,
        )

    @staticmethod
    def _to_optional_decimal(value) -> Optional[Decimal]:
        if value is None:
            return None
        return value if isinstance(value, Decimal) else Decimal(str(value))

    # ---------- READ ---------- #
    def get_price_for_date(self, stock_id: int, price_date: date) -> Optional[DailyPrice]:
        with self._provider.get_session() as session:
            row = session.query(ORMDailyPrice)\
                .filter(ORMDailyPrice.stock_id == stock_id, ORMDailyPrice.price_date == price_date)\
                .filter(ORMDailyPrice.close_price > 0)\
                .first()
            return self._to_domain(row) if row else None

    def get_prices_for_date(self, price_date: date) -> Dict[int, Decimal]:
        with self._provider.get_session() as session:
            rows = session.query(ORMDailyPrice.stock_id, ORMDailyPrice.close_price)\
                .filter(ORMDailyPrice.price_date == price_date)\
                .filter(ORMDailyPrice.close_price > 0)\
                .all()
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
                .filter(ORMDailyPrice.close_price > 0)\
                .order_by(ORMDailyPrice.price_date.desc())\
                .first()
            return self._to_domain(row) if row else None

    def get_price_series(self, stock_id: int, start_date: date, end_date: date) -> List[DailyPrice]:
        with self._provider.get_session() as session:
            rows = session.query(ORMDailyPrice)\
                .filter(ORMDailyPrice.stock_id == stock_id)\
                .filter(ORMDailyPrice.price_date >= start_date)\
                .filter(ORMDailyPrice.price_date <= end_date)\
                .filter(ORMDailyPrice.close_price > 0)\
                .order_by(ORMDailyPrice.price_date.asc()).all()
            return [self._to_domain(r) for r in rows]

    def get_price_series_bulk(
        self,
        stock_ids: Sequence[int],
        start_date: date,
        end_date: date,
    ) -> Dict[int, List[DailyPrice]]:
        if not stock_ids:
            return {}
        with self._provider.get_session() as session:
            rows = session.query(ORMDailyPrice)\
                .filter(ORMDailyPrice.stock_id.in_(stock_ids))\
                .filter(ORMDailyPrice.price_date >= start_date)\
                .filter(ORMDailyPrice.price_date <= end_date)\
                .filter(ORMDailyPrice.close_price > 0)\
                .order_by(ORMDailyPrice.price_date.asc()).all()
            result: Dict[int, List[DailyPrice]] = {sid: [] for sid in stock_ids}
            for r in rows:
                result[r.stock_id].append(self._to_domain(r))
            return result

    def get_portfolio_value_series(self, stock_ids: Sequence[int], start_date: date, end_date: date) -> Dict[date, Dict[int, Decimal]]:
        if not stock_ids:
            return {}
        with self._provider.get_session() as session:
            rows = session.query(ORMDailyPrice.stock_id, ORMDailyPrice.price_date, ORMDailyPrice.close_price)\
                .filter(ORMDailyPrice.stock_id.in_(stock_ids))\
                .filter(ORMDailyPrice.price_date >= start_date)\
                .filter(ORMDailyPrice.price_date <= end_date)\
                .filter(ORMDailyPrice.close_price > 0)\
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

    def get_price_dates_for_stock(self, stock_id: int, start_date: date, end_date: date) -> Set[date]:
        with self._provider.get_session() as session:
            rows = session.query(ORMDailyPrice.price_date)\
                .filter(ORMDailyPrice.stock_id == stock_id)\
                .filter(ORMDailyPrice.price_date >= start_date)\
                .filter(ORMDailyPrice.price_date <= end_date)\
                .filter(ORMDailyPrice.close_price > 0)\
                .all()
            return {row.price_date for row in rows}

    def get_latest_price_dates(self, stock_ids: Sequence[int]) -> Dict[int, date]:
        if not stock_ids:
            return {}
        with self._provider.get_session() as session:
            rows = session.query(ORMDailyPrice.stock_id, func.max(ORMDailyPrice.price_date).label("last_date"))\
                .filter(ORMDailyPrice.stock_id.in_(stock_ids))\
                .filter(ORMDailyPrice.close_price > 0)\
                .group_by(ORMDailyPrice.stock_id)\
                .all()
            return {row.stock_id: row.last_date for row in rows if row.last_date is not None}

    def get_price_presence_map(
        self,
        stock_ids: Sequence[int],
        start_date: date,
        end_date: date,
    ) -> Dict[int, Set[date]]:
        result: Dict[int, Set[date]] = {stock_id: set() for stock_id in stock_ids}
        if not stock_ids:
            return result
        with self._provider.get_session() as session:
            rows = session.query(ORMDailyPrice.stock_id, ORMDailyPrice.price_date)\
                .filter(ORMDailyPrice.stock_id.in_(stock_ids))\
                .filter(ORMDailyPrice.price_date >= start_date)\
                .filter(ORMDailyPrice.price_date <= end_date)\
                .filter(ORMDailyPrice.close_price > 0)\
                .order_by(ORMDailyPrice.stock_id.asc(), ORMDailyPrice.price_date.asc())\
                .all()
            for row in rows:
                result.setdefault(row.stock_id, set()).add(row.price_date)
        return result

    # ---------- WRITE (UPSERT) ---------- #
    def upsert_daily_price(self, daily_price: DailyPrice) -> DailyPrice:
        with self._provider.get_session() as session:
            is_sqlite = (session.bind.dialect.name == "sqlite")
            row_dict = self._to_row(daily_price)
            if is_sqlite:
                if "id" not in row_dict or row_dict["id"] is None:
                    max_id = session.execute(func.coalesce(func.max(ORMDailyPrice.id), 0)).scalar() or 0
                    row_dict["id"] = int(max_id) + 1

                stmt = sqlite_insert(ORMDailyPrice).values(**row_dict)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["stock_id", "price_date"],
                    set_={
                        "close_price": stmt.excluded.close_price,
                        "currency_code": stmt.excluded.currency_code,
                        "source": stmt.excluded.source,
                        "open_price": func.coalesce(stmt.excluded.open_price, ORMDailyPrice.open_price),
                        "high_price": func.coalesce(stmt.excluded.high_price, ORMDailyPrice.high_price),
                        "low_price": func.coalesce(stmt.excluded.low_price, ORMDailyPrice.low_price),
                        "volume": func.coalesce(stmt.excluded.volume, ORMDailyPrice.volume),
                    },
                )
            else:
                stmt = mysql_insert(ORMDailyPrice).values(**row_dict)
                stmt = stmt.on_duplicate_key_update(**self._upsert_update_columns(stmt))

            result = session.execute(stmt)
            commit_or_rollback(session)

            # last inserted id
            inserted_id = result.lastrowid
            return DailyPrice(
                id=inserted_id if inserted_id else (row_dict.get("id") or daily_price.id),
                stock_id=daily_price.stock_id,
                price_date=daily_price.price_date,
                close_price=daily_price.close_price,
                currency_code=daily_price.currency_code,
                source=daily_price.source,
                open_price=daily_price.open_price,
                high_price=daily_price.high_price,
                low_price=daily_price.low_price,
                volume=daily_price.volume,
            )

    def upsert_daily_prices_bulk(self, prices: Iterable[DailyPrice]) -> None:
        prices_list = list(prices)
        if not prices_list:
            return

        values = [self._to_row(p) for p in prices_list]
        chunk_size = 100

        with self._provider.get_session() as session:
            is_sqlite = (session.bind.dialect.name == "sqlite")
            if is_sqlite:
                max_id = session.execute(func.coalesce(func.max(ORMDailyPrice.id), 0)).scalar() or 0
                max_id = int(max_id)
                for item in values:
                    if "id" not in item or item["id"] is None:
                        max_id += 1
                        item["id"] = max_id

            for i in range(0, len(values), chunk_size):
                chunk = values[i : i + chunk_size]
                if is_sqlite:
                    stmt = sqlite_insert(ORMDailyPrice).values(chunk)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["stock_id", "price_date"],
                        set_={
                            "close_price": stmt.excluded.close_price,
                            "currency_code": stmt.excluded.currency_code,
                            "source": stmt.excluded.source,
                            "open_price": func.coalesce(stmt.excluded.open_price, ORMDailyPrice.open_price),
                            "high_price": func.coalesce(stmt.excluded.high_price, ORMDailyPrice.high_price),
                            "low_price": func.coalesce(stmt.excluded.low_price, ORMDailyPrice.low_price),
                            "volume": func.coalesce(stmt.excluded.volume, ORMDailyPrice.volume),
                        },
                    )
                else:
                    stmt = mysql_insert(ORMDailyPrice).values(chunk)
                    stmt = stmt.on_duplicate_key_update(**self._upsert_update_columns(stmt))

                session.execute(stmt)
            commit_or_rollback(session)

    @staticmethod
    def _to_row(p: DailyPrice) -> dict:
        return {
            "stock_id": p.stock_id,
            "price_date": p.price_date,
            "close_price": p.close_price,
            "currency_code": p.currency_code,
            "source": p.source,
            "open_price": p.open_price,
            "high_price": p.high_price,
            "low_price": p.low_price,
            "volume": p.volume,
        }

    @staticmethod
    def _upsert_update_columns(stmt) -> dict:
        # OHLCV kolonları COALESCE ile güncellenir: yeni değer NULL ise (örn. close-only
        # günlük fiyat güncelleme akışı) önceden backfill edilmiş OHLCV verisi silinmez.
        return {
            "close_price": stmt.inserted.close_price,
            "currency_code": stmt.inserted.currency_code,
            "source": stmt.inserted.source,
            "open_price": func.coalesce(stmt.inserted.open_price, ORMDailyPrice.open_price),
            "high_price": func.coalesce(stmt.inserted.high_price, ORMDailyPrice.high_price),
            "low_price": func.coalesce(stmt.inserted.low_price, ORMDailyPrice.low_price),
            "volume": func.coalesce(stmt.inserted.volume, ORMDailyPrice.volume),
        }

    def adjust_prices_before_date(self, stock_id: int, before_date: date, factor: Decimal) -> int:
        if factor <= 0:
            raise ValueError("Price adjustment factor must be positive")

        with self._provider.get_session() as session:
            updated_count = (
                session.query(ORMDailyPrice)
                .filter(ORMDailyPrice.stock_id == stock_id)
                .filter(ORMDailyPrice.price_date < before_date)
                .update(
                    {ORMDailyPrice.close_price: ORMDailyPrice.close_price * factor},
                    synchronize_session=False,
                )
            )
            commit_or_rollback(session)
            return int(updated_count or 0)

    def delete_all_prices(self) -> None:
        with self._provider.get_session() as session:
            session.query(ORMDailyPrice).delete()
            commit_or_rollback(session)

    def delete_prices_in_range(
        self,
        start_date: date,
        end_date: date,
        stock_ids: Sequence[int] | None = None,
    ) -> int:
        scoped_stock_ids = list(dict.fromkeys(stock_ids or [])) if stock_ids is not None else None
        if scoped_stock_ids == []:
            return 0
        with self._provider.get_session() as session:
            query = session.query(ORMDailyPrice)\
                .filter(ORMDailyPrice.price_date >= start_date)\
                .filter(ORMDailyPrice.price_date <= end_date)
            if scoped_stock_ids is not None:
                query = query.filter(ORMDailyPrice.stock_id.in_(scoped_stock_ids))
            deleted_count = query.delete(synchronize_session=False)
            commit_or_rollback(session)
            return deleted_count

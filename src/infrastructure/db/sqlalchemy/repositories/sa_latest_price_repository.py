from __future__ import annotations

from decimal import Decimal
from typing import Dict, Iterable, Sequence

from sqlalchemy import func
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.domain.models.latest_price import LatestPrice
from src.domain.ports.repositories.i_latest_price_repo import ILatestPriceRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMLatestPrice
from src.infrastructure.db.sqlalchemy.repositories._transaction import commit_or_rollback


class SQLAlchemyLatestPriceRepository(ILatestPriceRepository):
    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    def _to_domain(self, orm: ORMLatestPrice) -> LatestPrice:
        price = orm.price if isinstance(orm.price, Decimal) else Decimal(str(orm.price))
        return LatestPrice(
            id=orm.id,
            stock_id=orm.stock_id,
            price=price,
            as_of=orm.as_of,
            source=orm.source,
            provider=orm.provider,
            fetched_at=orm.fetched_at,
        )

    def get_latest_prices(self, stock_ids: Sequence[int]) -> Dict[int, LatestPrice]:
        if not stock_ids:
            return {}
        with self._provider.get_session() as session:
            rows = (
                session.query(ORMLatestPrice)
                .filter(ORMLatestPrice.stock_id.in_(stock_ids))
                .all()
            )
            return {row.stock_id: self._to_domain(row) for row in rows}

    def get_latest_price_map(self, stock_ids: Sequence[int]) -> Dict[int, Decimal]:
        if not stock_ids:
            return {}
        with self._provider.get_session() as session:
            rows = (
                session.query(ORMLatestPrice.stock_id, ORMLatestPrice.price)
                .filter(ORMLatestPrice.stock_id.in_(stock_ids))
                .all()
            )
            result: Dict[int, Decimal] = {}
            for row in rows:
                price = row.price if isinstance(row.price, Decimal) else Decimal(str(row.price))
                result[row.stock_id] = price
            return result

    def upsert_latest_prices(self, prices: Iterable[LatestPrice]) -> None:
        prices_list = list(prices)
        if not prices_list:
            return

        values = [
            {
                "stock_id": price.stock_id,
                "price": price.price,
                "as_of": price.as_of,
                "source": price.source,
                "provider": price.provider,
                "fetched_at": price.fetched_at,
            }
            for price in prices_list
        ]
        with self._provider.get_session() as session:
            if session.bind.dialect.name == "sqlite":
                self._upsert_sqlite(session, values)
                commit_or_rollback(session)
                return
            stmt = insert(ORMLatestPrice).values(values)
            stmt = stmt.on_duplicate_key_update(
                price=stmt.inserted.price,
                as_of=stmt.inserted.as_of,
                source=stmt.inserted.source,
                provider=stmt.inserted.provider,
                fetched_at=stmt.inserted.fetched_at,
                updated_at=func.now(),
            )
            session.execute(stmt)
            commit_or_rollback(session)

    @staticmethod
    def _upsert_sqlite(session, values: list) -> None:
        """SQLite: BIGINT birincil anahtar otomatik artmaz; yeni satırlara elle id verilir."""
        existing = {
            row.stock_id: row.id
            for row in session.query(ORMLatestPrice.stock_id, ORMLatestPrice.id)
            .filter(ORMLatestPrice.stock_id.in_([v["stock_id"] for v in values]))
            .all()
        }
        max_id = int(session.execute(func.coalesce(func.max(ORMLatestPrice.id), 0)).scalar() or 0)
        for item in values:
            row_id = existing.get(item["stock_id"])
            if row_id is None:
                max_id += 1
                row_id = max_id
            stmt = sqlite_insert(ORMLatestPrice).values(id=row_id, **item)
            stmt = stmt.on_conflict_do_update(
                index_elements=["stock_id"],
                set_={
                    "price": stmt.excluded.price,
                    "as_of": stmt.excluded.as_of,
                    "source": stmt.excluded.source,
                    "provider": stmt.excluded.provider,
                    "fetched_at": stmt.excluded.fetched_at,
                    "updated_at": func.now(),
                },
            )
            session.execute(stmt)

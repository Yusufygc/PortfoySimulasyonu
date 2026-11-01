from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Sequence

from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.domain.models.asset_price import AssetLatestPrice, AssetPrice
from src.domain.ports.repositories.i_asset_price_repo import IAssetPriceRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMAssetLatestPrice, ORMAssetPrice
from src.infrastructure.db.sqlalchemy.repositories._transaction import commit_or_rollback

_CHUNK = 500


def _decimal(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _daily_to_domain(orm: ORMAssetPrice) -> AssetPrice:
    return AssetPrice(
        id=orm.id,
        asset_id=orm.asset_id,
        price_date=orm.price_date,
        close_price=_decimal(orm.close_price),
        currency_code=orm.currency_code,
        source=orm.source,
    )


def _latest_to_domain(orm: ORMAssetLatestPrice) -> AssetLatestPrice:
    return AssetLatestPrice(
        id=orm.id,
        asset_id=orm.asset_id,
        price=_decimal(orm.price),
        currency_code=orm.currency_code,
        as_of=orm.as_of,
        source=orm.source,
        fetched_at=orm.fetched_at,
    )


class SQLAlchemyAssetPriceRepository(IAssetPriceRepository):
    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    def upsert_daily_prices(self, prices: Iterable[AssetPrice]) -> None:
        rows = [
            {
                "asset_id": p.asset_id,
                "price_date": p.price_date,
                "close_price": p.close_price,
                "currency_code": p.currency_code,
                "source": p.source,
            }
            for p in prices
        ]
        if not rows:
            return
        with self._provider.get_session() as session:
            for start in range(0, len(rows), _CHUNK):
                stmt = sqlite_insert(ORMAssetPrice).values(rows[start:start + _CHUNK])
                stmt = stmt.on_conflict_do_update(
                    index_elements=["asset_id", "price_date"],
                    set_={
                        "close_price": stmt.excluded.close_price,
                        "currency_code": stmt.excluded.currency_code,
                        "source": stmt.excluded.source,
                    },
                )
                session.execute(stmt)
            commit_or_rollback(session)

    def get_daily_prices(
        self, asset_id: int, start: Optional[date] = None, end: Optional[date] = None
    ) -> List[AssetPrice]:
        with self._provider.get_session() as session:
            query = session.query(ORMAssetPrice).filter(ORMAssetPrice.asset_id == asset_id)
            if start is not None:
                query = query.filter(ORMAssetPrice.price_date >= start)
            if end is not None:
                query = query.filter(ORMAssetPrice.price_date <= end)
            return [_daily_to_domain(row) for row in query.order_by(ORMAssetPrice.price_date).all()]

    def get_last_daily_price(self, asset_id: int, on_or_before: Optional[date] = None) -> Optional[AssetPrice]:
        with self._provider.get_session() as session:
            query = session.query(ORMAssetPrice).filter(ORMAssetPrice.asset_id == asset_id)
            if on_or_before is not None:
                query = query.filter(ORMAssetPrice.price_date <= on_or_before)
            row = query.order_by(ORMAssetPrice.price_date.desc()).first()
            return _daily_to_domain(row) if row is not None else None

    def upsert_latest_prices(self, prices: Iterable[AssetLatestPrice]) -> None:
        rows = [
            {
                "asset_id": p.asset_id,
                "price": p.price,
                "currency_code": p.currency_code,
                "as_of": p.as_of,
                "source": p.source,
                "fetched_at": p.fetched_at,
            }
            for p in prices
        ]
        if not rows:
            return
        with self._provider.get_session() as session:
            for row in rows:
                stmt = sqlite_insert(ORMAssetLatestPrice).values(**row)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["asset_id"],
                    set_={
                        "price": stmt.excluded.price,
                        "currency_code": stmt.excluded.currency_code,
                        "as_of": stmt.excluded.as_of,
                        "source": stmt.excluded.source,
                        "fetched_at": stmt.excluded.fetched_at,
                    },
                )
                session.execute(stmt)
            commit_or_rollback(session)

    def get_latest_prices(self, asset_ids: Sequence[int]) -> Dict[int, AssetLatestPrice]:
        if not asset_ids:
            return {}
        with self._provider.get_session() as session:
            rows = session.query(ORMAssetLatestPrice).filter(ORMAssetLatestPrice.asset_id.in_(asset_ids)).all()
            return {row.asset_id: _latest_to_domain(row) for row in rows}

    def get_latest_price_map(self, asset_ids: Sequence[int]) -> Dict[int, Decimal]:
        return {asset_id: latest.price for asset_id, latest in self.get_latest_prices(asset_ids).items()}

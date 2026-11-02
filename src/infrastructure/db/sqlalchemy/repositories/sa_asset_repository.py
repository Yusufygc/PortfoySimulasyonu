from __future__ import annotations

from typing import List, Optional

from sqlalchemy.exc import IntegrityError

from src.domain.models.asset import Asset, AssetClass
from src.domain.ports.repositories.i_asset_repo import IAssetRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMAsset, ORMAssetLatestPrice, ORMAssetPrice, ORMAssetTrade
from src.infrastructure.db.sqlalchemy.repositories._transaction import commit_or_rollback


def _to_domain(orm: ORMAsset) -> Asset:
    return Asset(
        id=orm.id,
        symbol=orm.symbol,
        name=orm.name,
        asset_class=AssetClass(orm.asset_class),
        quote_currency=orm.quote_currency,
        yf_symbol=orm.yf_symbol,
        unit=orm.unit,
        is_active=bool(orm.is_active),
        trade_currency=orm.trade_currency or "",
    )


def _to_orm(asset: Asset) -> ORMAsset:
    return ORMAsset(
        id=asset.id,
        symbol=asset.symbol,
        name=asset.name,
        asset_class=asset.asset_class.value,
        quote_currency=asset.quote_currency,
        yf_symbol=asset.yf_symbol,
        unit=asset.unit.value,
        is_active=asset.is_active,
        trade_currency=asset.trade_currency,
    )


class SQLAlchemyAssetRepository(IAssetRepository):
    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    def add_asset(self, asset: Asset) -> Asset:
        with self._provider.get_session() as session:
            orm_obj = _to_orm(asset)
            session.add(orm_obj)
            try:
                commit_or_rollback(session)
            except IntegrityError as exc:
                raise ValueError(f"Asset already exists: {asset.asset_class.value}/{asset.symbol}") from exc
            session.refresh(orm_obj)
            return _to_domain(orm_obj)

    def get_asset(self, asset_id: int) -> Optional[Asset]:
        with self._provider.get_session() as session:
            row = session.get(ORMAsset, asset_id)
            return _to_domain(row) if row is not None else None

    def get_asset_by_symbol(self, asset_class: AssetClass, symbol: str) -> Optional[Asset]:
        with self._provider.get_session() as session:
            row = (
                session.query(ORMAsset)
                .filter(ORMAsset.asset_class == asset_class.value, ORMAsset.symbol == symbol.strip().upper())
                .one_or_none()
            )
            return _to_domain(row) if row is not None else None

    def list_assets(self, active_only: bool = True) -> List[Asset]:
        with self._provider.get_session() as session:
            query = session.query(ORMAsset)
            if active_only:
                query = query.filter(ORMAsset.is_active.is_(True))
            return [_to_domain(row) for row in query.order_by(ORMAsset.asset_class, ORMAsset.symbol).all()]

    def set_active(self, asset_id: int, is_active: bool) -> None:
        with self._provider.get_session() as session:
            session.query(ORMAsset).filter(ORMAsset.id == asset_id).update({"is_active": is_active})
            commit_or_rollback(session)

    def delete_all_assets(self) -> None:
        with self._provider.get_session() as session:
            for model in (ORMAssetTrade, ORMAssetPrice, ORMAssetLatestPrice, ORMAsset):  # çocuk tablolar önce
                session.query(model).delete(synchronize_session=False)
            commit_or_rollback(session)

    def delete_asset(self, asset_id: int) -> None:
        with self._provider.get_session() as session:
            row = session.get(ORMAsset, asset_id)
            if row is not None:
                session.delete(row)
            commit_or_rollback(session)

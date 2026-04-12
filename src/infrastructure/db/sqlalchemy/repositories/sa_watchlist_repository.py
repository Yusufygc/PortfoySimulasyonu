# src/infrastructure/db/sqlalchemy/repositories/sa_watchlist_repository.py

from typing import List, Optional
from src.domain.models.watchlist import Watchlist, WatchlistItem
from src.domain.ports.repositories.i_watchlist_repo import IWatchlistRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMWatchlist, ORMWatchlistItem

class SQLAlchemyWatchlistRepository(IWatchlistRepository):
    """
    IWatchlistRepository arayüzünün SQLAlchemy tabanlı uygulaması.
    """

    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    # ---------- Mappers ---------- #
    def _to_domain_watchlist(self, orm: ORMWatchlist) -> Watchlist:
        return Watchlist(
            id=orm.id,
            name=orm.name,
            description=orm.description,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def _to_orm_watchlist(self, model: Watchlist) -> ORMWatchlist:
        return ORMWatchlist(
            id=model.id,
            name=model.name,
            description=model.description,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_domain_item(self, orm: ORMWatchlistItem) -> WatchlistItem:
        return WatchlistItem(
            id=orm.id,
            watchlist_id=orm.watchlist_id,
            stock_id=orm.stock_id,
            notes=orm.notes,
            added_at=orm.added_at,
        )

    def _to_orm_item(self, model: WatchlistItem) -> ORMWatchlistItem:
        return ORMWatchlistItem(
            id=model.id,
            watchlist_id=model.watchlist_id,
            stock_id=model.stock_id,
            notes=model.notes,
            added_at=model.added_at,
        )

    # ---------- Watchlist READ operasyonları ---------- #
    def get_all_watchlists(self) -> List[Watchlist]:
        with self._provider.get_session() as session:
            rows = session.query(ORMWatchlist).order_by(ORMWatchlist.name).all()
            return [self._to_domain_watchlist(r) for r in rows]

    def get_watchlist_by_id(self, watchlist_id: int) -> Optional[Watchlist]:
        with self._provider.get_session() as session:
            row = session.query(ORMWatchlist).filter_by(id=watchlist_id).first()
            return self._to_domain_watchlist(row) if row else None

    # ---------- Watchlist WRITE operasyonları ---------- #
    def create_watchlist(self, watchlist: Watchlist) -> Watchlist:
        with self._provider.get_session() as session:
            orm_obj = self._to_orm_watchlist(watchlist)
            session.add(orm_obj)
            session.commit()
            session.refresh(orm_obj)
            return self._to_domain_watchlist(orm_obj)

    def update_watchlist(self, watchlist: Watchlist) -> None:
        if watchlist.id is None:
            raise ValueError("Watchlist id is required for update")
        with self._provider.get_session() as session:
            orm_obj = session.query(ORMWatchlist).filter_by(id=watchlist.id).first()
            if orm_obj:
                orm_obj.name = watchlist.name
                orm_obj.description = watchlist.description
                session.commit()

    def delete_watchlist(self, watchlist_id: int) -> None:
        with self._provider.get_session() as session:
            orm_obj = session.query(ORMWatchlist).filter_by(id=watchlist_id).first()
            if orm_obj:
                session.delete(orm_obj)
                session.commit()

    # ---------- WatchlistItem READ operasyonları ---------- #
    def get_items_by_watchlist_id(self, watchlist_id: int) -> List[WatchlistItem]:
        with self._provider.get_session() as session:
            rows = session.query(ORMWatchlistItem)\
                .filter_by(watchlist_id=watchlist_id)\
                .order_by(ORMWatchlistItem.added_at.desc())\
                .all()
            return [self._to_domain_item(r) for r in rows]

    def get_item_by_id(self, item_id: int) -> Optional[WatchlistItem]:
        with self._provider.get_session() as session:
            row = session.query(ORMWatchlistItem).filter_by(id=item_id).first()
            return self._to_domain_item(row) if row else None

    # ---------- WatchlistItem WRITE operasyonları ---------- #
    def add_item_to_watchlist(self, item: WatchlistItem) -> WatchlistItem:
        with self._provider.get_session() as session:
            orm_obj = self._to_orm_item(item)
            session.add(orm_obj)
            session.commit()
            session.refresh(orm_obj)
            return self._to_domain_item(orm_obj)

    def remove_item_from_watchlist(self, item_id: int) -> None:
        with self._provider.get_session() as session:
            orm_obj = session.query(ORMWatchlistItem).filter_by(id=item_id).first()
            if orm_obj:
                session.delete(orm_obj)
                session.commit()

    def remove_stock_from_watchlist(self, watchlist_id: int, stock_id: int) -> None:
        with self._provider.get_session() as session:
            orm_obj = session.query(ORMWatchlistItem).filter_by(watchlist_id=watchlist_id, stock_id=stock_id).first()
            if orm_obj:
                session.delete(orm_obj)
                session.commit()

    def is_stock_in_watchlist(self, watchlist_id: int, stock_id: int) -> bool:
        with self._provider.get_session() as session:
            count = session.query(ORMWatchlistItem).filter_by(watchlist_id=watchlist_id, stock_id=stock_id).count()
            return count > 0

# src/infrastructure/db/watchlist_repository.py

from __future__ import annotations

from typing import List, Optional

from src.domain.models.watchlist import Watchlist, WatchlistItem
from src.domain.services_interfaces.i_watchlist_repo import IWatchlistRepository
from .mysql_connection import MySQLConnectionProvider


class MySQLWatchlistRepository(IWatchlistRepository):
    """
    IWatchlistRepository'nin MySQL implementasyonu.
    'watchlists' ve 'watchlist_items' tablolarına erişir.
    """

    def __init__(self, connection_provider: MySQLConnectionProvider) -> None:
        self._cp = connection_provider

    # ---------- Row → Domain Mappers ---------- #

    def _row_to_watchlist(self, row: dict) -> Watchlist:
        return Watchlist(
            id=row["id"],
            name=row["name"],
            description=row.get("description"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _row_to_watchlist_item(self, row: dict) -> WatchlistItem:
        return WatchlistItem(
            id=row["id"],
            watchlist_id=row["watchlist_id"],
            stock_id=row["stock_id"],
            notes=row.get("notes"),
            added_at=row.get("added_at"),
        )

    # ---------- Watchlist READ operasyonları ---------- #

    def get_all_watchlists(self) -> List[Watchlist]:
        sql = """
            SELECT id, name, description, created_at, updated_at
            FROM watchlists
            ORDER BY name
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql)
            rows = cursor.fetchall()

        return [self._row_to_watchlist(r) for r in rows]

    def get_watchlist_by_id(self, watchlist_id: int) -> Optional[Watchlist]:
        sql = """
            SELECT id, name, description, created_at, updated_at
            FROM watchlists
            WHERE id = %s
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (watchlist_id,))
            row = cursor.fetchone()

        if row is None:
            return None
        return self._row_to_watchlist(row)

    # ---------- Watchlist WRITE operasyonları ---------- #

    def create_watchlist(self, watchlist: Watchlist) -> Watchlist:
        sql = """
            INSERT INTO watchlists (name, description)
            VALUES (%s, %s)
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (watchlist.name, watchlist.description))
            watchlist_id = cursor.lastrowid

        return Watchlist(
            id=watchlist_id,
            name=watchlist.name,
            description=watchlist.description,
            created_at=None,
            updated_at=None,
        )

    def update_watchlist(self, watchlist: Watchlist) -> None:
        if watchlist.id is None:
            raise ValueError("Watchlist id is required for update")

        sql = """
            UPDATE watchlists
            SET name = %s,
                description = %s
            WHERE id = %s
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (watchlist.name, watchlist.description, watchlist.id))

    def delete_watchlist(self, watchlist_id: int) -> None:
        sql = "DELETE FROM watchlists WHERE id = %s"
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (watchlist_id,))

    # ---------- WatchlistItem READ operasyonları ---------- #

    def get_items_by_watchlist_id(self, watchlist_id: int) -> List[WatchlistItem]:
        sql = """
            SELECT id, watchlist_id, stock_id, notes, added_at
            FROM watchlist_items
            WHERE watchlist_id = %s
            ORDER BY added_at DESC
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (watchlist_id,))
            rows = cursor.fetchall()

        return [self._row_to_watchlist_item(r) for r in rows]

    def get_item_by_id(self, item_id: int) -> Optional[WatchlistItem]:
        sql = """
            SELECT id, watchlist_id, stock_id, notes, added_at
            FROM watchlist_items
            WHERE id = %s
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (item_id,))
            row = cursor.fetchone()

        if row is None:
            return None
        return self._row_to_watchlist_item(row)

    # ---------- WatchlistItem WRITE operasyonları ---------- #

    def add_item_to_watchlist(self, item: WatchlistItem) -> WatchlistItem:
        sql = """
            INSERT INTO watchlist_items (watchlist_id, stock_id, notes)
            VALUES (%s, %s, %s)
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (item.watchlist_id, item.stock_id, item.notes))
            item_id = cursor.lastrowid

        return WatchlistItem(
            id=item_id,
            watchlist_id=item.watchlist_id,
            stock_id=item.stock_id,
            notes=item.notes,
            added_at=None,
        )

    def remove_item_from_watchlist(self, item_id: int) -> None:
        sql = "DELETE FROM watchlist_items WHERE id = %s"
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (item_id,))

    def remove_stock_from_watchlist(self, watchlist_id: int, stock_id: int) -> None:
        sql = "DELETE FROM watchlist_items WHERE watchlist_id = %s AND stock_id = %s"
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (watchlist_id, stock_id))

    def is_stock_in_watchlist(self, watchlist_id: int, stock_id: int) -> bool:
        sql = """
            SELECT COUNT(*) as cnt
            FROM watchlist_items
            WHERE watchlist_id = %s AND stock_id = %s
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (watchlist_id, stock_id))
            row = cursor.fetchone()

        return row["cnt"] > 0 if row else False

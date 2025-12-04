# src/infrastructure/db/stock_repository.py

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from src.domain.models.stock import Stock
from src.domain.services_interfaces.i_stock_repo import IStockRepository
from .mysql_connection import MySQLConnectionProvider

class MySQLStockRepository(IStockRepository):
    """
    IStockRepository'nin MySQL implementasyonu.
    'stocks' tablosuna erişir.
    """

    def __init__(self, connection_provider: MySQLConnectionProvider) -> None:
        self._cp = connection_provider

    # ---------- Row → Domain Mapper ---------- #

    def _row_to_stock(self, row: dict) -> Stock:
        return Stock(
            id=row["id"],
            ticker=row["ticker"],
            name=row.get("name"),
            currency_code=row.get("currency_code", "TRY"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    # ---------- READ operasyonları ---------- #

    def get_all_stocks(self) -> List[Stock]:
        sql = """
            SELECT id, ticker, name, currency_code, created_at, updated_at
            FROM stocks
            ORDER BY ticker
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql)
            rows = cursor.fetchall()

        return [self._row_to_stock(r) for r in rows]

    def get_stock_by_id(self, stock_id: int) -> Optional[Stock]:
        sql = """
            SELECT id, ticker, name, currency_code, created_at, updated_at
            FROM stocks
            WHERE id = %s
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (stock_id,))
            row = cursor.fetchone()

        if row is None:
            return None
        return self._row_to_stock(row)

    def get_stock_by_ticker(self, ticker: str) -> Optional[Stock]:
        sql = """
            SELECT id, ticker, name, currency_code, created_at, updated_at
            FROM stocks
            WHERE ticker = %s
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (ticker,))
            row = cursor.fetchone()

        if row is None:
            return None
        return self._row_to_stock(row)

    def get_stocks_by_ids(self, stock_ids: Sequence[int]) -> List[Stock]:
        if not stock_ids:
            return []

        placeholders = ", ".join(["%s"] * len(stock_ids))
        sql = f"""
            SELECT id, ticker, name, currency_code, created_at, updated_at
            FROM stocks
            WHERE id IN ({placeholders})
            ORDER BY ticker
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, list(stock_ids))
            rows = cursor.fetchall()

        return [self._row_to_stock(r) for r in rows]

    def get_ticker_map_for_stock_ids(
        self,
        stock_ids: Sequence[int],
    ) -> Dict[int, str]:
        """
        { stock_id: ticker } döner.
        """
        if not stock_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(stock_ids))
        sql = f"""
            SELECT id, ticker
            FROM stocks
            WHERE id IN ({placeholders})
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, list(stock_ids))
            rows = cursor.fetchall()

        result: Dict[int, str] = {}
        for stock_id, ticker in rows:
            result[stock_id] = ticker
        return result

    # ---------- WRITE operasyonları ---------- #

    def insert_stock(self, stock: Stock) -> Stock:
        sql = """
            INSERT INTO stocks (ticker, name, currency_code)
            VALUES (%s, %s, %s)
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                sql,
                (
                    stock.ticker,
                    stock.name,
                    stock.currency_code,
                ),
            )
            stock_id = cursor.lastrowid

        return Stock(
            id=stock_id,
            ticker=stock.ticker,
            name=stock.name,
            currency_code=stock.currency_code,
            created_at=None,
            updated_at=None,
        )

    def insert_stocks_bulk(self, stocks: Iterable[Stock]) -> None:
        stocks_list = list(stocks)
        if not stocks_list:
            return

        sql = """
            INSERT INTO stocks (ticker, name, currency_code)
            VALUES (%s, %s, %s)
        """
        params = [
            (s.ticker, s.name, s.currency_code)
            for s in stocks_list
        ]

        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, params)

    def update_stock(self, stock: Stock) -> None:
        if stock.id is None:
            raise ValueError("Stock id is required for update")

        sql = """
            UPDATE stocks
            SET ticker = %s,
                name = %s,
                currency_code = %s
            WHERE id = %s
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                sql,
                (
                    stock.ticker,
                    stock.name,
                    stock.currency_code,
                    stock.id,
                ),
            )

    def delete_stock(self, stock_id: int) -> None:
        sql = "DELETE FROM stocks WHERE id = %s"
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (stock_id,))

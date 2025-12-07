# src/infrastructure/db/portfolio_repository.py

from __future__ import annotations

from datetime import date, time, datetime
from decimal import Decimal
from typing import Iterable, List, Optional, Sequence

from mysql.connector import MySQLConnection

from src.domain.models.trade import Trade, TradeSide
from src.domain.services_interfaces.i_portfolio_repo import IPortfolioRepository
from .mysql_connection import MySQLConnectionProvider

class MySQLPortfolioRepository(IPortfolioRepository):
    """
    IPortfolioRepository'nin MySQL implementasyonu.
    trades tablosuna erişir.
    """

    def __init__(self, connection_provider: MySQLConnectionProvider) -> None:
        self._cp = connection_provider

    # ---------- Row → Domain Mapper ---------- #

    def _row_to_trade(self, row: dict) -> Trade:
        """
        MySQL dict cursor row'unu Trade domain objesine çevirir.
        row:
          {
            "id": ...,
            "stock_id": ...,
            "trade_date": date,
            "trade_time": time veya None,
            "side": "BUY"/"SELL",
            "quantity": int,
            "price": Decimal/str/float,
          }
        """
        price_val = row["price"]
        if not isinstance(price_val, Decimal):
            price_val = Decimal(str(price_val))

        trade_time: Optional[time] = row.get("trade_time")
        return Trade(
            id=row["id"],
            stock_id=row["stock_id"],
            trade_date=row["trade_date"],
            trade_time=trade_time,
            side=TradeSide(row["side"]),
            quantity=row["quantity"],
            price=price_val,
        )

    # ---------- READ operasyonları ---------- #

    def get_all_trades(self) -> List[Trade]:
        sql = """
            SELECT id, stock_id, trade_date, trade_time, side, quantity, price
            FROM trades
            ORDER BY trade_date, trade_time, id
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql)
            rows = cursor.fetchall()

        return [self._row_to_trade(r) for r in rows]

    def get_trades_by_stock(self, stock_id: int) -> List[Trade]:
        sql = """
            SELECT id, stock_id, trade_date, trade_time, side, quantity, price
            FROM trades
            WHERE stock_id = %s
            ORDER BY trade_date, trade_time, id
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (stock_id,))
            rows = cursor.fetchall()

        return [self._row_to_trade(r) for r in rows]

    def get_trades_by_date_range(self, start_date: date, end_date: date) -> List[Trade]:
        sql = """
            SELECT id, stock_id, trade_date, trade_time, side, quantity, price
            FROM trades
            WHERE trade_date BETWEEN %s AND %s
            ORDER BY trade_date, trade_time, id
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (start_date, end_date))
            rows = cursor.fetchall()

        return [self._row_to_trade(r) for r in rows]

    def get_trade_by_id(self, trade_id: int) -> Optional[Trade]:
        sql = """
            SELECT id, stock_id, trade_date, trade_time, side, quantity, price
            FROM trades
            WHERE id = %s
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (trade_id,))
            row = cursor.fetchone()

        if row is None:
            return None
        return self._row_to_trade(row)

    def get_all_stock_ids_in_portfolio(self) -> Sequence[int]:
        """
        trades tablosundaki distinct stock_id'leri döner.
        """
        sql = """
            SELECT DISTINCT stock_id
            FROM trades
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()

        return [r[0] for r in rows]

    # ---------- WRITE operasyonları ---------- #

    def insert_trade(self, trade: Trade) -> Trade:
        sql = """
            INSERT INTO trades (stock_id, trade_date, trade_time, side, quantity, price)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                sql,
                (
                    trade.stock_id,
                    trade.trade_date,
                    trade.trade_time,
                    trade.side.value,
                    trade.quantity,
                    str(trade.price),
                ),
            )
            trade_id = cursor.lastrowid

        # Yeni id ile Trade objesini geri dönderiyoruz (immutable dataclass ise replace kullanılabilir).
        return Trade(
            id=trade_id,
            stock_id=trade.stock_id,
            trade_date=trade.trade_date,
            trade_time=trade.trade_time,
            side=trade.side,
            quantity=trade.quantity,
            price=trade.price,
        )

    def insert_trades_bulk(self, trades: Iterable[Trade]) -> None:
        sql = """
            INSERT INTO trades (stock_id, trade_date, trade_time, side, quantity, price)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = [
            (
                t.stock_id,
                t.trade_date,
                t.trade_time,
                t.side.value,
                t.quantity,
                str(t.price),
            )
            for t in trades
        ]

        if not params:
            return

        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, params)

    def update_trade(self, trade: Trade) -> None:
        if trade.id is None:
            raise ValueError("Trade id is required for update")

        sql = """
            UPDATE trades
            SET stock_id = %s,
                trade_date = %s,
                trade_time = %s,
                side = %s,
                quantity = %s,
                price = %s
            WHERE id = %s
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                sql,
                (
                    trade.stock_id,
                    trade.trade_date,
                    trade.trade_time,
                    trade.side.value,
                    trade.quantity,
                    str(trade.price),
                    trade.id,
                ),
            )

    def delete_trade(self, trade_id: int) -> None:
        sql = "DELETE FROM trades WHERE id = %s"
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (trade_id,))


    def delete_all_trades(self) -> None:
        """
        Tüm trades tablosunu temizler.
        """
        sql = "DELETE FROM trades"
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)

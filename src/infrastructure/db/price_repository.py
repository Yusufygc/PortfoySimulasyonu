# src/infrastructure/db/price_repository.py

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Sequence

from src.domain.models.daily_price import DailyPrice
from src.domain.services_interfaces.i_price_repo import IPriceRepository
from .mysql_connection import MySQLConnectionProvider

class MySQLPriceRepository(IPriceRepository):
    """
    IPriceRepository'nin MySQL implementasyonu.
    daily_prices tablosuna erişir.
    """

    def __init__(self, connection_provider: MySQLConnectionProvider) -> None:
        self._cp = connection_provider

    # ---------- Row → Domain Mapper ---------- #

    def _row_to_daily_price(self, row: dict) -> DailyPrice:
        price_val = row["close_price"]
        if not isinstance(price_val, Decimal):
            price_val = Decimal(str(price_val))

        return DailyPrice(
            id=row["id"],
            stock_id=row["stock_id"],
            price_date=row["price_date"],
            close_price=price_val,
            currency_code=row["currency_code"],
            source=row["source"],
        )

    # ---------- READ operasyonları ---------- #

    def get_price_for_date(self, stock_id: int, price_date: date) -> Optional[DailyPrice]:
        sql = """
            SELECT id, stock_id, price_date, close_price, currency_code, source
            FROM daily_prices
            WHERE stock_id = %s AND price_date = %s
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (stock_id, price_date))
            row = cursor.fetchone()

        if row is None:
            return None
        return self._row_to_daily_price(row)

    def get_prices_for_date(self, price_date: date) -> Dict[int, Decimal]:
        """
        { stock_id: close_price } map'i döner.
        """
        sql = """
            SELECT stock_id, close_price
            FROM daily_prices
            WHERE price_date = %s
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (price_date,))
            rows = cursor.fetchall()

        result: Dict[int, Decimal] = {}
        for stock_id, close_price in rows:
            if not isinstance(close_price, Decimal):
                close_price = Decimal(str(close_price))
            result[stock_id] = close_price
        return result

    def get_last_price_before(self, stock_id: int, price_date: date) -> Optional[DailyPrice]:
        sql = """
            SELECT id, stock_id, price_date, close_price, currency_code, source
            FROM daily_prices
            WHERE stock_id = %s AND price_date <= %s
            ORDER BY price_date DESC
            LIMIT 1
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (stock_id, price_date))
            row = cursor.fetchone()

        if row is None:
            return None
        return self._row_to_daily_price(row)

    def get_price_series(
        self,
        stock_id: int,
        start_date: date,
        end_date: date,
    ) -> List[DailyPrice]:
        sql = """
            SELECT id, stock_id, price_date, close_price, currency_code, source
            FROM daily_prices
            WHERE stock_id = %s AND price_date BETWEEN %s AND %s
            ORDER BY price_date
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (stock_id, start_date, end_date))
            rows = cursor.fetchall()

        return [self._row_to_daily_price(r) for r in rows]

    def get_portfolio_value_series(
        self,
        stock_ids: Sequence[int],
        start_date: date,
        end_date: date,
    ) -> Dict[date, Dict[int, Decimal]]:
        """
        Basit implementasyon: tüm stock_ids için fiyatları çekip memory'de grupluyoruz.
        Büyük portföy/prodda optimizasyon gerekir.
        """
        if not stock_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(stock_ids))
        sql = f"""
            SELECT stock_id, price_date, close_price
            FROM daily_prices
            WHERE stock_id IN ({placeholders})
              AND price_date BETWEEN %s AND %s
            ORDER BY price_date, stock_id
        """

        params = list(stock_ids) + [start_date, end_date]

        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        result: Dict[date, Dict[int, Decimal]] = {}
        for stock_id, price_date, close_price in rows:
            if not isinstance(close_price, Decimal):
                close_price = Decimal(str(close_price))
            if price_date not in result:
                result[price_date] = {}
            result[price_date][stock_id] = close_price

        return result

    # ---------- WRITE operasyonları (UPSERT) ---------- #

    def upsert_daily_price(self, daily_price: DailyPrice) -> DailyPrice:
        """
        MySQL 8 için INSERT ... ON DUPLICATE KEY UPDATE kullanıyoruz.
        UNIQUE(stock_id, price_date) constraint'ine dayanıyor.
        """
        sql = """
            INSERT INTO daily_prices (stock_id, price_date, close_price, currency_code, source)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                close_price = VALUES(close_price),
                currency_code = VALUES(currency_code),
                source = VALUES(source)
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                sql,
                (
                    daily_price.stock_id,
                    daily_price.price_date,
                    str(daily_price.close_price),
                    daily_price.currency_code,
                    daily_price.source,
                ),
            )
            # insert ise lastrowid, update ise 0 olabilir → yeniden select etmek istersen:
            inserted_id = cursor.lastrowid

        # id'yi garanti altına almak için (çok gerekmezse bile) tekrar select edebilirsin,
        # ama çoğu senaryoda id'ye çok ihtiyacın olmayacak.
        return DailyPrice(
            id=inserted_id if inserted_id != 0 else daily_price.id,
            stock_id=daily_price.stock_id,
            price_date=daily_price.price_date,
            close_price=daily_price.close_price,
            currency_code=daily_price.currency_code,
            source=daily_price.source,
        )

    def upsert_daily_prices_bulk(self, prices: Iterable[DailyPrice]) -> None:
        prices_list = list(prices)
        if not prices_list:
            return

        sql = """
            INSERT INTO daily_prices (stock_id, price_date, close_price, currency_code, source)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                close_price = VALUES(close_price),
                currency_code = VALUES(currency_code),
                source = VALUES(source)
        """
        params = [
            (
                p.stock_id,
                p.price_date,
                str(p.close_price),
                p.currency_code,
                p.source,
            )
            for p in prices_list
        ]

        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, params)

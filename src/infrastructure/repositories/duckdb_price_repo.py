"""
DuckDBPriceRepository — IPriceRepository arayüzünün DuckDB tabanlı analitik uygulaması.

Özellikler:
- Gömülü, ultra hızlı sütunsal (columnar) depolama (data/market_history.duckdb)
- Vektörel sorgu motoru ile sıfır kopyalama (zero-copy) Pandas/Arrow desteği
- SQLite OLTP veritabanından bağımsız; lock contention ve şişmeyi önler
- IPriceRepository ile %100 uyumluluk (stock_id <-> ticker çift yönlü cache)
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set

import duckdb
import pandas as pd

from src.domain.models.daily_price import DailyPrice
from src.domain.ports.repositories.i_price_repo import IPriceRepository

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "data/market_history.duckdb"


class DuckDBPriceRepository(IPriceRepository):
    """
    DuckDB tabanlı yüksek performanslı fiyat deposu.
    """

    def __init__(
        self,
        db_path: str = _DEFAULT_DB_PATH,
        stock_repo=None,
    ) -> None:
        self._db_path = db_path
        self._stock_repo = stock_repo

        # stock_id <-> ticker mapping önbelleği
        self._ticker_by_id: Dict[int, str] = {}
        self._id_by_ticker: Dict[str, int] = {}

        # Dizin ve şema kontrolü
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        self._refresh_mappings()

    def _get_connection(self, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        """Yeni veya thread-safe bağlantı döndürür."""
        return duckdb.connect(self._db_path, read_only=read_only)

    def _init_schema(self) -> None:
        """Tablolar yoksa oluşturur."""
        with self._get_connection(read_only=False) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS bist_stocks (
                    ticker VARCHAR PRIMARY KEY,
                    name VARCHAR,
                    currency_code VARCHAR DEFAULT 'TRY',
                    first_date DATE,
                    last_date DATE,
                    total_bars INTEGER
                );
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS daily_prices (
                    ticker VARCHAR,
                    price_date DATE,
                    open_price DOUBLE,
                    high_price DOUBLE,
                    low_price DOUBLE,
                    close_price DOUBLE,
                    volume BIGINT,
                    PRIMARY KEY (ticker, price_date)
                );
            """)

    def _refresh_mappings(self) -> None:
        """stock_repo varsa ID <-> ticker haritasını tazeler."""
        if self._stock_repo:
            try:
                stocks = self._stock_repo.get_all_stocks()
                for s in stocks:
                    if s.id is not None:
                        clean_tk = s.ticker.replace(".IS", "").strip().upper()
                        self._ticker_by_id[s.id] = clean_tk
                        self._id_by_ticker[clean_tk] = s.id
            except Exception as exc:
                logger.warning("DuckDBPriceRepository: stock_repo mappings okunamadı: %s", exc)

    def _resolve_ticker(self, stock_id: int) -> Optional[str]:
        if stock_id in self._ticker_by_id:
            return self._ticker_by_id[stock_id]
        self._refresh_mappings()
        return self._ticker_by_id.get(stock_id)

    def _resolve_id(self, ticker: str) -> int:
        clean = ticker.replace(".IS", "").strip().upper()
        if clean in self._id_by_ticker:
            return self._id_by_ticker[clean]
        self._refresh_mappings()
        if clean in self._id_by_ticker:
            return self._id_by_ticker[clean]
        # Fallback: deterministik hash tabanlı sanal id
        virtual_id = abs(hash(clean)) % 10000000 + 10000
        self._id_by_ticker[clean] = virtual_id
        self._ticker_by_id[virtual_id] = clean
        return virtual_id

    # ──────────────────────────── Mapper ────────────────────────────

    def _row_to_domain(self, row, stock_id: int) -> DailyPrice:
        # row: (ticker, price_date, open, high, low, close, volume)
        p_date = row[1]
        if isinstance(p_date, (datetime, pd.Timestamp)):
            p_date = p_date.date()

        close_val = Decimal(str(row[5])) if row[5] is not None else Decimal("0")
        open_val = Decimal(str(row[2])) if row[2] is not None else None
        high_val = Decimal(str(row[3])) if row[3] is not None else None
        low_val = Decimal(str(row[4])) if row[4] is not None else None
        vol = int(row[6]) if row[6] is not None else 0

        return DailyPrice(
            id=None,
            stock_id=stock_id,
            price_date=p_date,
            close_price=close_val,
            currency_code="TRY",
            source="duckdb",
            open_price=open_val,
            high_price=high_val,
            low_price=low_val,
            volume=vol,
        )

    # ──────────────────────────── READ ────────────────────────────

    def get_price_for_date(self, stock_id: int, price_date: date) -> Optional[DailyPrice]:
        ticker = self._resolve_ticker(stock_id)
        if not ticker:
            return None
        with self._get_connection(read_only=True) as con:
            res = con.execute("""
                SELECT ticker, price_date, open_price, high_price, low_price, close_price, volume
                FROM daily_prices
                WHERE ticker = ? AND price_date = ? AND close_price > 0
            """, [ticker, price_date]).fetchone()
            return self._row_to_domain(res, stock_id) if res else None

    def get_prices_for_date(self, price_date: date) -> Dict[int, Decimal]:
        with self._get_connection(read_only=True) as con:
            rows = con.execute("""
                SELECT ticker, close_price
                FROM daily_prices
                WHERE price_date = ? AND close_price > 0
            """, [price_date]).fetchall()
            res: Dict[int, Decimal] = {}
            for tk, cp in rows:
                sid = self._resolve_id(tk)
                res[sid] = Decimal(str(cp))
            return res

    def get_last_price_before(self, stock_id: int, price_date: date) -> Optional[DailyPrice]:
        ticker = self._resolve_ticker(stock_id)
        if not ticker:
            return None
        with self._get_connection(read_only=True) as con:
            res = con.execute("""
                SELECT ticker, price_date, open_price, high_price, low_price, close_price, volume
                FROM daily_prices
                WHERE ticker = ? AND price_date <= ? AND close_price > 0
                ORDER BY price_date DESC
                LIMIT 1
            """, [ticker, price_date]).fetchone()
            return self._row_to_domain(res, stock_id) if res else None

    def get_price_series(self, stock_id: int, start_date: date, end_date: date) -> List[DailyPrice]:
        ticker = self._resolve_ticker(stock_id)
        if not ticker:
            return []
        with self._get_connection(read_only=True) as con:
            rows = con.execute("""
                SELECT ticker, price_date, open_price, high_price, low_price, close_price, volume
                FROM daily_prices
                WHERE ticker = ? AND price_date >= ? AND price_date <= ? AND close_price > 0
                ORDER BY price_date ASC
            """, [ticker, start_date, end_date]).fetchall()
            return [self._row_to_domain(r, stock_id) for r in rows]

    def get_price_series_bulk(
        self,
        stock_ids: Sequence[int],
        start_date: date,
        end_date: date,
    ) -> Dict[int, List[DailyPrice]]:
        if not stock_ids:
            return {}
        result: Dict[int, List[DailyPrice]] = {sid: [] for sid in stock_ids}
        tickers_map = {self._resolve_ticker(sid): sid for sid in stock_ids if self._resolve_ticker(sid)}
        if not tickers_map:
            return result

        tickers = list(tickers_map.keys())
        with self._get_connection(read_only=True) as con:
            rows = con.execute("""
                SELECT ticker, price_date, open_price, high_price, low_price, close_price, volume
                FROM daily_prices
                WHERE ticker = ANY(?) AND price_date >= ? AND price_date <= ? AND close_price > 0
                ORDER BY price_date ASC
            """, [tickers, start_date, end_date]).fetchall()
            for r in rows:
                tk = r[0]
                sid = tickers_map.get(tk)
                if sid is not None:
                    result[sid].append(self._row_to_domain(r, sid))
        return result

    def get_portfolio_value_series(
        self,
        stock_ids: Sequence[int],
        start_date: date,
        end_date: date,
    ) -> Dict[date, Dict[int, Decimal]]:
        if not stock_ids:
            return {}
        tickers_map = {self._resolve_ticker(sid): sid for sid in stock_ids if self._resolve_ticker(sid)}
        if not tickers_map:
            return {}

        tickers = list(tickers_map.keys())
        with self._get_connection(read_only=True) as con:
            rows = con.execute("""
                SELECT price_date, ticker, close_price
                FROM daily_prices
                WHERE ticker = ANY(?) AND price_date >= ? AND price_date <= ? AND close_price > 0
                ORDER BY price_date ASC
            """, [tickers, start_date, end_date]).fetchall()

            result: Dict[date, Dict[int, Decimal]] = {}
            for p_date, tk, cp in rows:
                if isinstance(p_date, (datetime, pd.Timestamp)):
                    p_date = p_date.date()
                sid = tickers_map.get(tk)
                if sid is not None:
                    if p_date not in result:
                        result[p_date] = {}
                    result[p_date][sid] = Decimal(str(cp))
            return result

    def get_price_dates_for_stock(self, stock_id: int, start_date: date, end_date: date) -> Set[date]:
        ticker = self._resolve_ticker(stock_id)
        if not ticker:
            return set()
        with self._get_connection(read_only=True) as con:
            rows = con.execute("""
                SELECT price_date
                FROM daily_prices
                WHERE ticker = ? AND price_date >= ? AND price_date <= ? AND close_price > 0
            """, [ticker, start_date, end_date]).fetchall()
            return {
                r[0].date() if isinstance(r[0], (datetime, pd.Timestamp)) else r[0]
                for r in rows
            }

    def get_latest_price_dates(self, stock_ids: Sequence[int]) -> Dict[int, date]:
        if not stock_ids:
            return {}
        tickers_map = {self._resolve_ticker(sid): sid for sid in stock_ids if self._resolve_ticker(sid)}
        if not tickers_map:
            return {}

        tickers = list(tickers_map.keys())
        with self._get_connection(read_only=True) as con:
            rows = con.execute("""
                SELECT ticker, MAX(price_date)
                FROM daily_prices
                WHERE ticker = ANY(?) AND close_price > 0
                GROUP BY ticker
            """, [tickers]).fetchall()
            res = {}
            for tk, max_d in rows:
                if max_d is not None:
                    p_date = max_d.date() if isinstance(max_d, (datetime, pd.Timestamp)) else max_d
                    sid = tickers_map.get(tk)
                    if sid is not None:
                        res[sid] = p_date
            return res

    def get_price_presence_map(
        self,
        stock_ids: Sequence[int],
        start_date: date,
        end_date: date,
    ) -> Dict[int, Set[date]]:
        result: Dict[int, Set[date]] = {stock_id: set() for stock_id in stock_ids}
        if not stock_ids:
            return result
        tickers_map = {self._resolve_ticker(sid): sid for sid in stock_ids if self._resolve_ticker(sid)}
        if not tickers_map:
            return result

        tickers = list(tickers_map.keys())
        with self._get_connection(read_only=True) as con:
            rows = con.execute("""
                SELECT ticker, price_date
                FROM daily_prices
                WHERE ticker = ANY(?) AND price_date >= ? AND price_date <= ? AND close_price > 0
                ORDER BY price_date ASC
            """, [tickers, start_date, end_date]).fetchall()
            for tk, p_date in rows:
                p_date = p_date.date() if isinstance(p_date, (datetime, pd.Timestamp)) else p_date
                sid = tickers_map.get(tk)
                if sid is not None:
                    result[sid].add(p_date)
        return result

    # ──────────────────────────── WRITE (UPSERT) ────────────────────────────

    def upsert_daily_price(self, daily_price: DailyPrice) -> DailyPrice:
        ticker = self._resolve_ticker(daily_price.stock_id)
        if not ticker:
            raise ValueError(f"stock_id={daily_price.stock_id} için ticker çözümlenemedi")

        o = float(daily_price.open_price) if daily_price.open_price is not None else None
        h = float(daily_price.high_price) if daily_price.high_price is not None else None
        l = float(daily_price.low_price) if daily_price.low_price is not None else None
        c = float(daily_price.close_price) if daily_price.close_price is not None else 0.0
        v = int(daily_price.volume) if daily_price.volume is not None else 0

        with self._get_connection(read_only=False) as con:
            con.execute("""
                INSERT OR REPLACE INTO daily_prices (ticker, price_date, open_price, high_price, low_price, close_price, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [ticker, daily_price.price_date, o, h, l, c, v])
        return daily_price

    def upsert_daily_prices_bulk(self, prices: Iterable[DailyPrice]) -> None:
        prices_list = list(prices)
        if not prices_list:
            return

        rows = []
        for p in prices_list:
            tk = self._resolve_ticker(p.stock_id)
            if not tk:
                continue
            rows.append((
                tk,
                p.price_date,
                float(p.open_price) if p.open_price is not None else None,
                float(p.high_price) if p.high_price is not None else None,
                float(p.low_price) if p.low_price is not None else None,
                float(p.close_price) if p.close_price is not None else 0.0,
                int(p.volume) if p.volume is not None else 0,
            ))

        if not rows:
            return

        with self._get_connection(read_only=False) as con:
            # DuckDB appender / bulk executemany
            con.executemany("""
                INSERT OR REPLACE INTO daily_prices (ticker, price_date, open_price, high_price, low_price, close_price, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, rows)

    def adjust_prices_before_date(self, stock_id: int, before_date: date, factor: Decimal) -> int:
        ticker = self._resolve_ticker(stock_id)
        if not ticker:
            return 0
        if factor <= 0:
            raise ValueError("Price adjustment factor must be positive")

        f_val = float(factor)
        with self._get_connection(read_only=False) as con:
            con.execute("""
                UPDATE daily_prices
                SET close_price = close_price * ?,
                    open_price = open_price * ?,
                    high_price = high_price * ?,
                    low_price = low_price * ?
                WHERE ticker = ? AND price_date < ?
            """, [f_val, f_val, f_val, f_val, ticker, before_date])
            return 1

    def delete_all_prices(self) -> None:
        with self._get_connection(read_only=False) as con:
            con.execute("DELETE FROM daily_prices")

    def delete_prices_in_range(
        self,
        start_date: date,
        end_date: date,
        stock_ids: Sequence[int] | None = None,
    ) -> int:
        with self._get_connection(read_only=False) as con:
            if stock_ids is not None:
                tickers = [self._resolve_ticker(sid) for sid in stock_ids if self._resolve_ticker(sid)]
                if not tickers:
                    return 0
                con.execute("""
                    DELETE FROM daily_prices
                    WHERE price_date >= ? AND price_date <= ? AND ticker = ANY(?)
                """, [start_date, end_date, tickers])
            else:
                con.execute("""
                    DELETE FROM daily_prices
                    WHERE price_date >= ? AND price_date <= ?
                """, [start_date, end_date])
            return 1

    # ──────────────────────────── DUCKDB NATIVE EKSTRA METODLAR ────────────────────────────

    def get_price_series_by_ticker(
        self,
        ticker: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[DailyPrice]:
        """Doğrudan ticker ile sorgular; stock_id çözümlemesi gerekmez."""
        clean = ticker.replace(".IS", "").strip().upper()
        stock_id = self._resolve_id(clean)

        query = "SELECT ticker, price_date, open_price, high_price, low_price, close_price, volume FROM daily_prices WHERE ticker = ?"
        params = [clean]

        if start_date:
            query += " AND price_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND price_date <= ?"
            params.append(end_date)
        query += " ORDER BY price_date ASC"

        with self._get_connection(read_only=True) as con:
            rows = con.execute(query, params).fetchall()
            return [self._row_to_domain(r, stock_id) for r in rows]

    def get_dataframe(
        self,
        ticker: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """Pandas DataFrame formatında sıfır kopyalama ile anında döndürür."""
        clean = ticker.replace(".IS", "").strip().upper()
        query = "SELECT price_date, open_price as open, high_price as high, low_price as low, close_price as close, volume FROM daily_prices WHERE ticker = ?"
        params = [clean]

        if start_date:
            query += " AND price_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND price_date <= ?"
            params.append(end_date)
        query += " ORDER BY price_date ASC"

        with self._get_connection(read_only=True) as con:
            return con.execute(query, params).df()

    def get_all_tickers(self) -> List[str]:
        """Veritabanında kayıtlı tüm hisse sembollerini döndürür."""
        with self._get_connection(read_only=True) as con:
            rows = con.execute("SELECT DISTINCT ticker FROM daily_prices ORDER BY ticker").fetchall()
            return [r[0] for r in rows]

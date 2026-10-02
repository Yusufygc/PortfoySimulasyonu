"""DuckDB piyasa geçmişi (OLAP) okuyucusu — salt okunur, her çağrıda kısa ömürlü bağlantı."""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import List, Optional

import duckdb

from src.domain.models.market_bar import MarketBar
from src.domain.ports.repositories.i_market_history_repo import IMarketHistoryRepository
from src.infrastructure.db.paths import duckdb_path

logger = logging.getLogger(__name__)


def clean_ticker(ticker: str) -> str:
    return (ticker or "").strip().upper().replace(".IS", "")


class DuckDBMarketHistoryRepository(IMarketHistoryRepository):
    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else duckdb_path()

    def is_available(self) -> bool:
        return self._db_path.exists()

    def _query(self, sql: str, params: list) -> list:
        """Salt okunur bağlantıyla sorgular. Dosya yoksa, kilitliyse veya tablo yoksa boş döner."""
        if not self._db_path.exists():
            return []
        try:
            con = duckdb.connect(str(self._db_path), read_only=True)
        except Exception as exc:
            logger.debug("DuckDB bağlantısı açılamadı (%s): %s", self._db_path, exc)
            return []
        try:
            return con.execute(sql, params).fetchall()
        except Exception as exc:
            logger.debug("DuckDB sorgusu başarısız: %s", exc)
            return []
        finally:
            con.close()

    @staticmethod
    def _to_bar(ticker: str, row) -> Optional[MarketBar]:
        price_date, open_p, high_p, low_p, close_p, volume = row
        if close_p is None or close_p <= 0:
            return None
        return MarketBar(
            ticker=ticker,
            price_date=price_date,
            close_price=float(close_p),
            open_price=float(open_p) if open_p is not None else None,
            high_price=float(high_p) if high_p is not None else None,
            low_price=float(low_p) if low_p is not None else None,
            volume=int(volume) if volume is not None else None,
        )

    def get_price_series(self, ticker: str, start_date: date, end_date: date) -> List[MarketBar]:
        clean = clean_ticker(ticker)
        rows = self._query(
            "SELECT price_date, open_price, high_price, low_price, close_price, volume FROM daily_prices "
            "WHERE ticker = ? AND price_date >= ? AND price_date <= ? ORDER BY price_date",
            [clean, start_date, end_date],
        )
        return [bar for bar in (self._to_bar(clean, row) for row in rows) if bar is not None]

    def get_last_bars(self, ticker: str, count: int = 2) -> List[MarketBar]:
        clean = clean_ticker(ticker)
        rows = self._query(
            "SELECT price_date, open_price, high_price, low_price, close_price, volume FROM daily_prices "
            "WHERE ticker = ? AND close_price IS NOT NULL AND close_price > 0 ORDER BY price_date DESC LIMIT ?",
            [clean, int(count)],
        )
        return [bar for bar in (self._to_bar(clean, row) for row in rows) if bar is not None]

    def has_ticker(self, ticker: str) -> bool:
        return bool(self._query("SELECT 1 FROM bist_stocks WHERE ticker = ? LIMIT 1", [clean_ticker(ticker)]))

    def get_company_name(self, ticker: str) -> Optional[str]:
        rows = self._query("SELECT name FROM bist_stocks WHERE ticker = ? LIMIT 1", [clean_ticker(ticker)])
        return rows[0][0] if rows and rows[0][0] else None

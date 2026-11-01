"""DuckDB piyasa geçmişinin yazma tarafı (`IMarketHistoryStore`): artımlı senkronun DuckDB işlemleri."""
from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import duckdb
import pandas as pd

from src.domain.models.market_bar import MarketBar
from src.domain.ports.repositories.i_market_history_store import IMarketHistoryStore
from src.infrastructure.db.paths import duckdb_path as default_duckdb_path

logger = logging.getLogger(__name__)

_BAR_COLUMNS = ["ticker", "price_date", "open_price", "high_price", "low_price", "close_price", "volume"]
_INVALID_WHERE = "WHERE (close_price IS NULL OR close_price <= 0) AND price_date >= ? AND price_date <= ?"


def _as_date(value) -> Optional[date]:
    return value.date() if isinstance(value, datetime) else value


def _optional_float(value) -> Optional[float]:
    return None if value is None or value != value else float(value)


class DuckDBMarketHistoryStore(IMarketHistoryStore):
    def __init__(self, duckdb_path: Optional[str] = None) -> None:
        self._path = str(duckdb_path) if duckdb_path else str(default_duckdb_path())

    @property
    def path(self) -> str:
        return self._path

    def connect(self, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        return duckdb.connect(self._path, read_only=read_only)

    def exists(self) -> bool:
        return Path(self._path).exists()

    def last_bar_date(self) -> Optional[date]:
        if not self.exists():
            return None
        try:
            with self.connect(read_only=True) as con:
                row = con.execute("SELECT MAX(last_date) FROM bist_stocks").fetchone()
        except Exception as exc:
            logger.warning("DuckDB max_date okunamadı: %s", exc)
            return None
        return _as_date(row[0]) if row and row[0] else None

    def list_tickers(self) -> List[str]:
        with self.connect(read_only=True) as con:
            return [r[0] for r in con.execute("SELECT ticker FROM bist_stocks ORDER BY ticker").fetchall()]

    def invalid_bars(self, start: date, end: date) -> Tuple[Optional[date], int, List[Tuple[str, date]]]:
        if not self.exists():
            return None, 0, []
        params = [start, end]
        try:
            with self.connect(read_only=True) as con:
                row = con.execute(f"SELECT MIN(price_date), COUNT(*) FROM daily_prices {_INVALID_WHERE}", params).fetchone()
                sample = con.execute(
                    f"SELECT ticker, price_date FROM daily_prices {_INVALID_WHERE} ORDER BY price_date, ticker LIMIT 10",
                    params,
                ).fetchall() if row and row[1] else []
        except Exception as exc:
            logger.debug("Geçersiz bar taraması başarısız: %s", exc)
            return None, 0, []
        return (_as_date(row[0]) if row else None), (int(row[1]) if row else 0), [(t, _as_date(d)) for t, d in sample]

    def write_bars(self, bars: Sequence[MarketBar]) -> None:
        if not bars:
            return
        frame = pd.DataFrame([
            (b.ticker, b.price_date, b.open_price, b.high_price, b.low_price, b.close_price, b.volume) for b in bars
        ], columns=_BAR_COLUMNS)
        with self.connect(read_only=False) as con:
            con.register("temp_delta", frame)
            con.execute("""
                INSERT OR REPLACE INTO daily_prices
                SELECT ticker, price_date, open_price, high_price, low_price, close_price, volume
                FROM temp_delta
            """)
            # Yeniden indirilemeyen (kısmi/hayalet) geçersiz kapanışlı barlar yeni veriyle değiştirildi; kalanlar atılır
            con.execute("DELETE FROM daily_prices WHERE close_price IS NULL OR close_price <= 0")
            con.execute("""
                UPDATE bist_stocks
                SET last_date = sub.max_d,
                    total_bars = sub.cnt,
                    updated_at = ?
                FROM (
                    SELECT ticker, MAX(price_date) as max_d, COUNT(*) as cnt
                    FROM daily_prices
                    GROUP BY ticker
                ) sub
                WHERE bist_stocks.ticker = sub.ticker
            """, [datetime.now()])
            con.unregister("temp_delta")

    def bars_after(self, after: date, tickers: Sequence[str]) -> List[MarketBar]:
        if not self.exists() or not tickers:
            return []
        with self.connect(read_only=True) as con:
            rows = con.execute(
                "SELECT ticker, price_date, open_price, high_price, low_price, close_price, volume "
                "FROM daily_prices WHERE close_price > 0 AND price_date > ? AND ticker IN (SELECT UNNEST(?))",
                [after, list(tickers)],
            ).fetchall()
        return [
            MarketBar(
                ticker=t, price_date=_as_date(d), close_price=float(c), open_price=_optional_float(o),
                high_price=_optional_float(h), low_price=_optional_float(lo),
                volume=None if v is None else int(v),
            )
            for t, d, o, h, lo, c, v in rows
        ]

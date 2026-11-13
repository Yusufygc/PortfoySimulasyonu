"""DuckDB piyasa geçmişi (OLAP) okuyucusu — salt okunur, her çağrıda kısa ömürlü bağlantı."""
from __future__ import annotations

import logging
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import duckdb

from src.domain.models.market_bar import MarketBar
from src.domain.models.market_corporate_action import MarketCorporateAction, PriceBreak, cumulative_factor
from src.domain.ports.repositories.i_market_history_repo import IMarketHistoryRepository
from src.infrastructure.db.paths import duckdb_path
from src.infrastructure.market_data.duckdb_corporate_action_store import DuckDBCorporateActionStore

logger = logging.getLogger(__name__)


def clean_ticker(ticker: str) -> str:
    return (ticker or "").strip().upper().replace(".IS", "")


class DuckDBMarketHistoryRepository(IMarketHistoryRepository):
    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else duckdb_path()
        self._actions = DuckDBCorporateActionStore(self._db_path)

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

    @staticmethod
    def _adjust(bars: List[MarketBar], actions: List[MarketCorporateAction]) -> List[MarketBar]:
        """Onaylı olayların faktörlerini OHLC'ye uygular; hacim ham kalır."""
        if not actions:
            return bars
        adjusted: List[MarketBar] = []
        for bar in bars:
            factor = cumulative_factor(actions, bar.price_date)
            if factor == 1.0:
                adjusted.append(bar)
                continue
            adjusted.append(replace(
                bar,
                close_price=bar.close_price * factor,
                open_price=None if bar.open_price is None else bar.open_price * factor,
                high_price=None if bar.high_price is None else bar.high_price * factor,
                low_price=None if bar.low_price is None else bar.low_price * factor,
            ))
        return adjusted

    def get_price_series(
        self, ticker: str, start_date: date, end_date: date, adjusted: bool = True
    ) -> List[MarketBar]:
        clean = clean_ticker(ticker)
        rows = self._query(
            "SELECT price_date, open_price, high_price, low_price, close_price, volume FROM daily_prices "
            "WHERE ticker = ? AND price_date >= ? AND price_date <= ? ORDER BY price_date",
            [clean, start_date, end_date],
        )
        bars = [bar for bar in (self._to_bar(clean, row) for row in rows) if bar is not None]
        return self._adjust(bars, self._actions.list_actions_for_adjustment(clean)) if adjusted else bars

    def get_last_bars(self, ticker: str, count: int = 2, adjusted: bool = True) -> List[MarketBar]:
        clean = clean_ticker(ticker)
        rows = self._query(
            "SELECT price_date, open_price, high_price, low_price, close_price, volume FROM daily_prices "
            "WHERE ticker = ? AND close_price IS NOT NULL AND close_price > 0 ORDER BY price_date DESC LIMIT ?",
            [clean, int(count)],
        )
        bars = [bar for bar in (self._to_bar(clean, row) for row in rows) if bar is not None]
        return self._adjust(bars, self._actions.list_actions_for_adjustment(clean)) if adjusted else bars

    def has_ticker(self, ticker: str) -> bool:
        return bool(self._query("SELECT 1 FROM bist_stocks WHERE ticker = ? LIMIT 1", [clean_ticker(ticker)]))

    def get_company_name(self, ticker: str) -> Optional[str]:
        rows = self._query("SELECT name FROM bist_stocks WHERE ticker = ? LIMIT 1", [clean_ticker(ticker)])
        return rows[0][0] if rows and rows[0][0] else None

    def list_tickers(self) -> List[str]:
        rows = self._query("SELECT ticker FROM bist_stocks ORDER BY ticker", [])
        return [row[0] for row in rows if row[0]]

    def get_price_series_bulk(
        self, tickers: Sequence[str], start_date: date, end_date: date, adjusted: bool = True
    ) -> Dict[str, List[MarketBar]]:
        cleaned = sorted({clean_ticker(t) for t in tickers if t})
        if not cleaned:
            return {}
        rows = self._query(
            "SELECT ticker, price_date, open_price, high_price, low_price, close_price, volume FROM daily_prices "
            "WHERE ticker IN (SELECT UNNEST(?)) AND price_date >= ? AND price_date <= ? "
            "ORDER BY ticker, price_date",
            [cleaned, start_date, end_date],
        )
        result: Dict[str, List[MarketBar]] = {}
        for row in rows:
            bar = self._to_bar(row[0], row[1:])
            if bar is not None:
                result.setdefault(row[0], []).append(bar)
        if adjusted:
            by_ticker = self._actions.active_actions_by_ticker()
            result = {tk: self._adjust(bars, by_ticker.get(tk, [])) for tk, bars in result.items()}
        return result

    def find_price_breaks(
        self, min_date: date, drop_ratio: float = 1.25, rise_ratio: float = 2.0
    ) -> List[PriceBreak]:
        rows = self._query(
            """
            WITH v AS (
                SELECT ticker, price_date, close_price, volume,
                       LAG(close_price) OVER w AS prev_close, LAG(price_date) OVER w AS prev_date,
                       LAG(volume) OVER w AS prev_volume, LAG(close_price, 2) OVER w AS prev2_close,
                       LEAD(close_price, 1) OVER w AS n1, LEAD(close_price, 2) OVER w AS n2,
                       LEAD(close_price, 3) OVER w AS n3
                FROM daily_prices
                WHERE close_price IS NOT NULL AND close_price > 0
                WINDOW w AS (PARTITION BY ticker ORDER BY price_date)
            ), r AS (
                SELECT *, prev_close / close_price AS ratio FROM v WHERE prev_close IS NOT NULL
            ), m AS (
                SELECT price_date, MEDIAN(ratio) AS market_ratio FROM r WHERE price_date >= ? GROUP BY price_date
            )
            SELECT r.ticker, r.price_date, r.prev_date, r.prev_close, r.close_price, r.volume, r.prev_volume,
                   r.prev2_close, r.n1, r.n2, r.n3, m.market_ratio
            FROM r JOIN m USING (price_date)
            WHERE r.price_date >= ? AND (r.ratio >= ? OR r.ratio <= ?)
            ORDER BY r.ticker, r.price_date
            """,
            [min_date, min_date, float(drop_ratio), 1.0 / float(rise_ratio)],
        )
        return [
            PriceBreak(
                ticker=row[0], price_date=row[1], prev_date=row[2], prev_close=float(row[3]), close=float(row[4]),
                volume=None if row[5] is None else int(row[5]),
                prev_volume=None if row[6] is None else int(row[6]),
                prev2_close=None if row[7] is None else float(row[7]),
                next_closes=tuple(float(v) for v in row[8:11] if v is not None),
                market_ratio=None if row[11] is None else float(row[11]),
            )
            for row in rows
        ]

    def get_latest_dates(self) -> Dict[str, date]:
        rows = self._query(
            "SELECT ticker, MAX(price_date) FROM daily_prices WHERE close_price IS NOT NULL AND close_price > 0 "
            "GROUP BY ticker",
            [],
        )
        return {row[0]: row[1] for row in rows if row[1] is not None}

"""DuckDB `market_corporate_actions` tablosu: ticker bazlı kurumsal aksiyonlar ve fiyat düzeltme faktörleri.

Okuma salt okunur kısa ömürlü bağlantıyla yapılır (dosya/tablo yoksa boş döner). Yazma yalnızca bu sınıf,
`MarketDataSyncService` ve `BistBulkDownloader` üzerinden olur; ham `daily_prices` barlarına dokunulmaz.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

import duckdb

from src.domain.models.market_corporate_action import (
    MarketActionSource,
    MarketActionStatus,
    MarketActionType,
    MarketCorporateAction,
)
from src.domain.ports.repositories.i_market_corporate_action_repo import IMarketCorporateActionRepository
from src.infrastructure.db.paths import duckdb_path

logger = logging.getLogger(__name__)

TABLE = "market_corporate_actions"
_COLUMNS = (
    "ticker, effective_date, factor, action_type, status, source, ex_date, ratio, rights_price, "
    "observed_ratio, confidence, note"
)

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    ticker VARCHAR NOT NULL,
    effective_date DATE NOT NULL,
    factor DOUBLE NOT NULL,
    action_type VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    source VARCHAR NOT NULL,
    ex_date DATE,
    ratio DOUBLE,
    rights_price DOUBLE,
    observed_ratio DOUBLE,
    confidence DOUBLE,
    note VARCHAR,
    updated_at TIMESTAMP,
    PRIMARY KEY (ticker, effective_date)
)
"""


def clean_ticker(ticker: str) -> str:
    return (ticker or "").strip().upper().replace(".IS", "")


def ensure_schema(con: "duckdb.DuckDBPyConnection") -> None:
    con.execute(CREATE_TABLE_SQL)


def _to_date(value) -> Optional[date]:
    return value.date() if isinstance(value, datetime) else value


def _row_to_action(row) -> MarketCorporateAction:
    (ticker, effective_date, factor, action_type, status, source, ex_date, ratio, rights_price,
     observed_ratio, confidence, note) = row
    return MarketCorporateAction(
        ticker=ticker,
        effective_date=_to_date(effective_date),
        factor=float(factor),
        action_type=MarketActionType(action_type),
        status=MarketActionStatus(status),
        source=MarketActionSource(source),
        ex_date=_to_date(ex_date),
        ratio=ratio,
        rights_price=rights_price,
        observed_ratio=observed_ratio,
        confidence=confidence,
        note=note or "",
    )


class DuckDBCorporateActionStore(IMarketCorporateActionRepository):
    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else duckdb_path()

    # ---- okuma -------------------------------------------------------------------------
    def _read(self, sql: str, params: list) -> list:
        if not self._db_path.exists():
            return []
        try:
            con = duckdb.connect(str(self._db_path), read_only=True)
        except Exception as exc:
            logger.debug("Kurumsal aksiyon deposu açılamadı: %s", exc)
            return []
        try:
            return con.execute(sql, params).fetchall()
        except Exception as exc:  # tablo henüz yok vb.
            logger.debug("Kurumsal aksiyon sorgusu başarısız: %s", exc)
            return []
        finally:
            con.close()

    def list_actions(
        self,
        ticker: Optional[str] = None,
        status: Optional[MarketActionStatus] = None,
    ) -> List[MarketCorporateAction]:
        where, params = [], []
        if ticker:
            where.append("ticker = ?")
            params.append(clean_ticker(ticker))
        if status:
            where.append("status = ?")
            params.append(status.value)
        clause = f" WHERE {' AND '.join(where)}" if where else ""
        rows = self._read(f"SELECT {_COLUMNS} FROM {TABLE}{clause} ORDER BY ticker, effective_date", params)
        return [_row_to_action(row) for row in rows]

    def active_actions_by_ticker(self) -> Dict[str, List[MarketCorporateAction]]:
        result: Dict[str, List[MarketCorporateAction]] = {}
        for action in self.list_actions(status=MarketActionStatus.CONFIRMED):
            result.setdefault(action.ticker, []).append(action)
        return result

    def list_actions_for_adjustment(self, ticker: str) -> List[MarketCorporateAction]:
        """Bir hissenin düzeltmede kullanılacak (ONAYLI) olayları."""
        return self.list_actions(ticker=ticker, status=MarketActionStatus.CONFIRMED)

    # ---- yazma -------------------------------------------------------------------------
    def _write(self, fn) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect(str(self._db_path), read_only=False)
        try:
            ensure_schema(con)
            return fn(con)
        finally:
            con.close()

    def upsert(self, action: MarketCorporateAction) -> None:
        def run(con):
            con.execute(
                f"INSERT OR REPLACE INTO {TABLE} ({_COLUMNS}, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [
                    clean_ticker(action.ticker), action.effective_date, action.factor, action.action_type.value,
                    action.status.value, action.source.value, action.ex_date, action.ratio, action.rights_price,
                    action.observed_ratio, action.confidence, action.note, datetime.now(),
                ],
            )

        self._write(run)

    def set_status(self, ticker: str, effective_date: date, status: MarketActionStatus) -> bool:
        def run(con):
            before = con.execute(
                f"SELECT COUNT(*) FROM {TABLE} WHERE ticker = ? AND effective_date = ?",
                [clean_ticker(ticker), effective_date],
            ).fetchone()[0]
            if before:
                con.execute(
                    f"UPDATE {TABLE} SET status = ?, updated_at = ? WHERE ticker = ? AND effective_date = ?",
                    [status.value, datetime.now(), clean_ticker(ticker), effective_date],
                )
            return bool(before)

        return self._write(run)

    def delete(self, ticker: str, effective_date: date) -> bool:
        def run(con):
            before = con.execute(
                f"SELECT COUNT(*) FROM {TABLE} WHERE ticker = ? AND effective_date = ?",
                [clean_ticker(ticker), effective_date],
            ).fetchone()[0]
            con.execute(
                f"DELETE FROM {TABLE} WHERE ticker = ? AND effective_date = ?",
                [clean_ticker(ticker), effective_date],
            )
            return bool(before)

        return self._write(run)

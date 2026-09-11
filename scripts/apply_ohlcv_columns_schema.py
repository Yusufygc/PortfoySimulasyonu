"""daily_prices tablosuna OHLCV kolonlarını (open/high/low/volume) idempotent ekler.

ATR, Stochastic, CCI, VWAP, OBV gibi indikatörler için gerekli (bkz.
TRANSFORMATION_PLAN.md Faz 2). Kolonlar nullable — eski kayıtlar etkilenmez.

Migration öncesi scripts/backup_mysql.py ile yedek alınmış olmalı
(bkz. ARCHITECTURE_GATES.md §3.2 — ALTER TABLE yedeksiz çalıştırılmaz).
"""
from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.application.container import AppContainer

_NEW_COLUMNS = {
    "open_price": "NUMERIC(18, 4) NULL",
    "high_price": "NUMERIC(18, 4) NULL",
    "low_price": "NUMERIC(18, 4) NULL",
    "volume": "BIGINT UNSIGNED NULL",
}


def _existing_columns(session, table_name: str) -> set[str]:
    rows = session.execute(
        text(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table"
        ),
        {"table": table_name},
    ).fetchall()
    return {row[0] for row in rows}


def main() -> None:
    container = AppContainer()
    with container.conn_provider.get_session() as session:
        existing = _existing_columns(session, "daily_prices")
        missing = {name: ddl for name, ddl in _NEW_COLUMNS.items() if name not in existing}

        if not missing:
            print("daily_prices: OHLCV kolonları zaten mevcut, işlem yapılmadı.")
            return

        for name, ddl in missing.items():
            session.execute(text(f"ALTER TABLE daily_prices ADD COLUMN {name} {ddl}"))
            print(f"daily_prices.{name} eklendi.")
        session.commit()

    print(f"daily_prices şeması güncellendi: {len(missing)} yeni kolon.")


if __name__ == "__main__":
    main()

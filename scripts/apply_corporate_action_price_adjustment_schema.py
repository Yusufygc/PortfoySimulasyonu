"""Apply corporate_actions price-adjustment schema changes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings_loader import load_app_settings
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider


COLUMNS = {
    "prices_adjusted": (
        "ALTER TABLE corporate_actions "
        "ADD COLUMN prices_adjusted TINYINT(1) NOT NULL DEFAULT 0 AFTER applied_at"
    ),
    "prices_adjusted_at": (
        "ALTER TABLE corporate_actions "
        "ADD COLUMN prices_adjusted_at DATETIME NULL AFTER prices_adjusted"
    ),
    "price_adjustment_factor": (
        "ALTER TABLE corporate_actions "
        "ADD COLUMN price_adjustment_factor DECIMAL(18, 10) NULL AFTER prices_adjusted_at"
    ),
    "price_adjustment_count": (
        "ALTER TABLE corporate_actions "
        "ADD COLUMN price_adjustment_count INT NOT NULL DEFAULT 0 AFTER price_adjustment_factor"
    ),
}


def main() -> int:
    provider = SQLAlchemyEngineProvider(load_app_settings().db)
    try:
        with provider._engine.begin() as conn:
            conn.exec_driver_sql(
                "ALTER TABLE corporate_actions MODIFY COLUMN ratio DECIMAL(12, 8) NOT NULL"
            )
            existing_columns = {
                row[0]
                for row in conn.exec_driver_sql(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = DATABASE() AND table_name = 'corporate_actions'"
                )
            }
            for column_name, ddl in COLUMNS.items():
                if column_name not in existing_columns:
                    conn.exec_driver_sql(ddl)

            has_index = conn.exec_driver_sql(
                "SELECT COUNT(*) FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() AND table_name = 'corporate_actions' "
                "AND index_name = 'idx_corporate_actions_price_adjusted'"
            ).scalar()
            if not has_index:
                conn.exec_driver_sql(
                    "CREATE INDEX idx_corporate_actions_price_adjusted "
                    "ON corporate_actions (prices_adjusted)"
                )
    finally:
        provider.dispose()

    print("schema-migration-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

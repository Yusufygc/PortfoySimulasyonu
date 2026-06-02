"""Apply corporate_action_candidates schema changes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings_loader import load_app_settings
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS corporate_action_candidates (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    ticker VARCHAR(20) NOT NULL,
    stock_id BIGINT UNSIGNED NULL,
    source VARCHAR(30) NOT NULL,
    source_disclosure_id VARCHAR(100) NOT NULL,
    source_url VARCHAR(500) NULL,
    action_type ENUM('BEDELLI', 'BEDELSIZ') NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'DISCOVERED',
    ratio DECIMAL(12, 8) NULL,
    subscription_price DECIMAL(18, 4) NULL,
    announcement_date DATE NULL,
    ex_date DATE NULL,
    confidence DECIMAL(5, 4) NOT NULL DEFAULT 0,
    raw_payload_json JSON NULL,
    parse_notes VARCHAR(500) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT uq_corp_action_candidate_source
        UNIQUE (source, source_disclosure_id, action_type, ticker),
    CONSTRAINT fk_corp_action_candidates_stock
        FOREIGN KEY (stock_id) REFERENCES stocks(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_corp_action_candidates_ticker_status_exdate (ticker, status, ex_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def main() -> int:
    provider = SQLAlchemyEngineProvider(load_app_settings().db)
    try:
        with provider._engine.begin() as conn:
            conn.exec_driver_sql(CREATE_TABLE)
    finally:
        provider.dispose()
    print("candidate-schema-migration-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

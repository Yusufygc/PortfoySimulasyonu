"""KAP Ortaklık Yapısı için 3 tabloyu oluştur (idempotent)."""
from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.application.container import AppContainer


CREATE_KAP_COMPANIES_SQL = """
CREATE TABLE IF NOT EXISTS kap_companies (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    ticker VARCHAR(20) NOT NULL,
    mkk_member_oid VARCHAR(40) NOT NULL,
    title VARCHAR(255) NULL,
    last_fetched_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT uq_kap_companies_ticker UNIQUE (ticker),
    INDEX idx_kap_companies_oid (mkk_member_oid)
)
"""

CREATE_KAP_SNAPSHOTS_SQL = """
CREATE TABLE IF NOT EXISTS kap_shareholder_snapshots (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    company_id BIGINT UNSIGNED NOT NULL,
    creation_date DATE NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT uq_kap_shareholder_snapshot UNIQUE (company_id, creation_date),
    CONSTRAINT fk_kap_snap_company FOREIGN KEY (company_id)
        REFERENCES kap_companies(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    INDEX idx_kap_shareholder_snap_date (creation_date)
)
"""

CREATE_KAP_ROWS_SQL = """
CREATE TABLE IF NOT EXISTS kap_shareholder_rows (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    snapshot_id BIGINT UNSIGNED NOT NULL,
    shareholder_name VARCHAR(500) NOT NULL,
    share_in_capital NUMERIC(24, 4) NULL,
    ratio_in_capital NUMERIC(9, 4) NULL,
    voting_right_ratio NUMERIC(9, 4) NULL,
    is_total TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    CONSTRAINT fk_kap_row_snap FOREIGN KEY (snapshot_id)
        REFERENCES kap_shareholder_snapshots(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    INDEX idx_kap_shareholder_rows_snap (snapshot_id)
)
"""


def main() -> None:
    container = AppContainer()
    with container.conn_provider.get_session() as session:
        session.execute(text(CREATE_KAP_COMPANIES_SQL))
        session.execute(text(CREATE_KAP_SNAPSHOTS_SQL))
        session.execute(text(CREATE_KAP_ROWS_SQL))
        session.commit()
    print("KAP shareholder schema is ready (kap_companies, kap_shareholder_snapshots, kap_shareholder_rows).")


if __name__ == "__main__":
    main()

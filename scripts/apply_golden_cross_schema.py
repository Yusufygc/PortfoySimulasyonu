"""golden_cross_events tablosunu idempotent oluştur."""
from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.application.container import AppContainer


CREATE_GOLDEN_CROSS_SQL = """
CREATE TABLE IF NOT EXISTS golden_cross_events (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    stock_id BIGINT UNSIGNED NOT NULL,
    cross_date DATE NOT NULL,
    cross_type ENUM('GOLDEN', 'DEATH') NOT NULL,
    short_ma NUMERIC(18, 4) NULL,
    long_ma NUMERIC(18, 4) NULL,
    close_price NUMERIC(18, 4) NOT NULL,
    detected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT uq_golden_cross_event UNIQUE (stock_id, cross_date, cross_type),
    CONSTRAINT fk_golden_cross_stock FOREIGN KEY (stock_id)
        REFERENCES stocks(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    INDEX idx_golden_cross_date (cross_date),
    INDEX idx_golden_cross_type_date (cross_type, cross_date)
)
"""


def main() -> None:
    container = AppContainer()
    with container.conn_provider.get_session() as session:
        session.execute(text(CREATE_GOLDEN_CROSS_SQL))
        session.commit()
    print("golden_cross_events schema is ready.")


if __name__ == "__main__":
    main()

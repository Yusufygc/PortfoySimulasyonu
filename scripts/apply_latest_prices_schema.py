from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.application.container import AppContainer


CREATE_LATEST_PRICES_SQL = """
CREATE TABLE IF NOT EXISTS latest_prices (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    stock_id BIGINT UNSIGNED NOT NULL,
    price NUMERIC(18, 4) NOT NULL,
    as_of DATETIME NOT NULL,
    source VARCHAR(50) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    fetched_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT uq_latest_prices_stock UNIQUE (stock_id),
    CONSTRAINT fk_latest_prices_stock FOREIGN KEY (stock_id)
        REFERENCES stocks(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    INDEX idx_latest_prices_as_of (as_of)
)
"""


def main() -> None:
    container = AppContainer()
    with container.conn_provider.get_session() as session:
        session.execute(text(CREATE_LATEST_PRICES_SQL))
        session.commit()
    print("latest_prices schema is ready.")


if __name__ == "__main__":
    main()

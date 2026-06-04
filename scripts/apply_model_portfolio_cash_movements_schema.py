"""Apply model_portfolio_cash_movements schema changes."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings_loader import load_app_settings
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS model_portfolio_cash_movements (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    portfolio_id INT NOT NULL,
    movement_date DATE NOT NULL,
    movement_time TIME NULL,
    type ENUM('DEPOSIT', 'WITHDRAW') NOT NULL,
    amount DECIMAL(18, 4) NOT NULL,
    notes VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_model_portfolio_cash_movements_portfolio
        FOREIGN KEY (portfolio_id) REFERENCES model_portfolios(id)
        ON DELETE CASCADE,
    INDEX idx_model_portfolio_cash_movements_portfolio_date (portfolio_id, movement_date, movement_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def main() -> int:
    provider = SQLAlchemyEngineProvider(load_app_settings().db)
    try:
        with provider._engine.begin() as conn:
            conn.exec_driver_sql(CREATE_TABLE)
    finally:
        provider.dispose()
    print("model-portfolio-cash-movements-schema-ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

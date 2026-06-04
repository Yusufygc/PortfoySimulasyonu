"""Apply trade adjustments and original trade columns schema changes."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings_loader import load_app_settings
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider

def main() -> int:
    provider = SQLAlchemyEngineProvider(load_app_settings().db)
    try:
        with provider._engine.begin() as conn:
            # 1. Check existing columns in 'trades' table
            existing_columns = {
                row[0]
                for row in conn.exec_driver_sql(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = DATABASE() AND table_name = 'trades'"
                )
            }
            
            # Add original_quantity
            if "original_quantity" not in existing_columns:
                print("Adding original_quantity column...")
                conn.exec_driver_sql(
                    "ALTER TABLE trades ADD COLUMN original_quantity BIGINT UNSIGNED NULL AFTER price"
                )
                
            # Add original_price
            if "original_price" not in existing_columns:
                print("Adding original_price column...")
                conn.exec_driver_sql(
                    "ALTER TABLE trades ADD COLUMN original_price DECIMAL(18, 4) NULL AFTER original_quantity"
                )
                
            # 2. Populate original_quantity and original_price if they are NULL
            print("Populating original columns with current values...")
            conn.exec_driver_sql(
                "UPDATE trades SET original_quantity = quantity WHERE original_quantity IS NULL"
            )
            conn.exec_driver_sql(
                "UPDATE trades SET original_price = price WHERE original_price IS NULL"
            )
            
            # Make columns NOT NULL
            print("Making columns NOT NULL...")
            conn.exec_driver_sql(
                "ALTER TABLE trades MODIFY COLUMN original_quantity BIGINT UNSIGNED NOT NULL"
            )
            conn.exec_driver_sql(
                "ALTER TABLE trades MODIFY COLUMN original_price DECIMAL(18, 4) NOT NULL"
            )
            
            # 3. Create trade_adjustments table if not exists
            print("Creating trade_adjustments table...")
            conn.exec_driver_sql(
                """
                CREATE TABLE IF NOT EXISTS trade_adjustments (
                    id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
                    trade_id BIGINT UNSIGNED NOT NULL,
                    corporate_action_id BIGINT UNSIGNED NOT NULL,
                    factor DECIMAL(18, 10) NOT NULL,
                    pre_quantity BIGINT UNSIGNED NOT NULL,
                    post_quantity BIGINT UNSIGNED NOT NULL,
                    pre_price DECIMAL(18, 4) NOT NULL,
                    post_price DECIMAL(18, 4) NOT NULL,
                    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE,
                    FOREIGN KEY (corporate_action_id) REFERENCES corporate_actions(id) ON DELETE RESTRICT
                )
                """
            )
            
            # Add index on trade_id
            has_index = conn.exec_driver_sql(
                "SELECT COUNT(*) FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() AND table_name = 'trade_adjustments' "
                "AND index_name = 'idx_trade_adjustments_trade'"
            ).scalar()
            if not has_index:
                print("Creating index for trade_adjustments...")
                conn.exec_driver_sql(
                    "CREATE INDEX idx_trade_adjustments_trade ON trade_adjustments (trade_id)"
                )
                
    except Exception as e:
        print(f"Error during migration: {e}")
        return 1
    finally:
        provider.dispose()

    print("schema-migration-ok")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

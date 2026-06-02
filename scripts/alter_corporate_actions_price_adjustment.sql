-- Corporate action price-adjustment tracking columns.
-- Run once on existing databases before using the MERKO repair flow.

USE portfoySim;

SET @schema_name = DATABASE();

ALTER TABLE corporate_actions
    MODIFY COLUMN ratio DECIMAL(12, 8) NOT NULL;

SET @ddl = (
    SELECT IF(
        COUNT(*) = 0,
        'ALTER TABLE corporate_actions ADD COLUMN prices_adjusted TINYINT(1) NOT NULL DEFAULT 0 AFTER applied_at',
        'SELECT ''prices_adjusted already exists'''
    )
    FROM information_schema.columns
    WHERE table_schema = @schema_name
      AND table_name = 'corporate_actions'
      AND column_name = 'prices_adjusted'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @ddl = (
    SELECT IF(
        COUNT(*) = 0,
        'ALTER TABLE corporate_actions ADD COLUMN prices_adjusted_at DATETIME NULL AFTER prices_adjusted',
        'SELECT ''prices_adjusted_at already exists'''
    )
    FROM information_schema.columns
    WHERE table_schema = @schema_name
      AND table_name = 'corporate_actions'
      AND column_name = 'prices_adjusted_at'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @ddl = (
    SELECT IF(
        COUNT(*) = 0,
        'ALTER TABLE corporate_actions ADD COLUMN price_adjustment_factor DECIMAL(18, 10) NULL AFTER prices_adjusted_at',
        'SELECT ''price_adjustment_factor already exists'''
    )
    FROM information_schema.columns
    WHERE table_schema = @schema_name
      AND table_name = 'corporate_actions'
      AND column_name = 'price_adjustment_factor'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @ddl = (
    SELECT IF(
        COUNT(*) = 0,
        'ALTER TABLE corporate_actions ADD COLUMN price_adjustment_count INT NOT NULL DEFAULT 0 AFTER price_adjustment_factor',
        'SELECT ''price_adjustment_count already exists'''
    )
    FROM information_schema.columns
    WHERE table_schema = @schema_name
      AND table_name = 'corporate_actions'
      AND column_name = 'price_adjustment_count'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @ddl = (
    SELECT IF(
        COUNT(*) = 0,
        'CREATE INDEX idx_corporate_actions_price_adjusted ON corporate_actions (prices_adjusted)',
        'SELECT ''idx_corporate_actions_price_adjusted already exists'''
    )
    FROM information_schema.statistics
    WHERE table_schema = @schema_name
      AND table_name = 'corporate_actions'
      AND index_name = 'idx_corporate_actions_price_adjusted'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

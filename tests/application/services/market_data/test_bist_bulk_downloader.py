from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from src.application.services.market_data.bist_bulk_downloader import BistBulkDownloader


@pytest.fixture
def temp_downloader(tmp_path):
    db_file = str(tmp_path / "bulk_test.duckdb")
    return BistBulkDownloader(db_path=db_file, max_workers=2)


def test_bist_bulk_downloader_init(temp_downloader):
    downloader = temp_downloader
    with downloader._get_connection() as con:
        tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
        assert "daily_prices" in tables
        assert "bist_stocks" in tables


def test_save_stock_history(temp_downloader):
    downloader = temp_downloader
    df = pd.DataFrame([
        {
            "ticker": "GARAN",
            "price_date": pd.to_datetime("2026-01-01").date(),
            "open_price": 100.0,
            "high_price": 105.0,
            "low_price": 99.0,
            "close_price": 104.0,
            "volume": 50000,
        },
        {
            "ticker": "GARAN",
            "price_date": pd.to_datetime("2026-01-02").date(),
            "open_price": 104.0,
            "high_price": 108.0,
            "low_price": 103.0,
            "close_price": 107.0,
            "volume": 60000,
        },
    ])

    saved = downloader.save_stock_history(df)
    assert saved == 2

    with downloader._get_connection() as con:
        count = con.execute("SELECT COUNT(*) FROM daily_prices WHERE ticker = 'GARAN'").fetchone()[0]
        assert count == 2
        stock_row = con.execute("SELECT total_bars FROM bist_stocks WHERE ticker = 'GARAN'").fetchone()
        assert stock_row[0] == 2

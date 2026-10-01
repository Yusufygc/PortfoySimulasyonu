from datetime import date, datetime, time as dt_time, timedelta
import pytest
from unittest.mock import MagicMock

from src.application.services.market_data.market_data_sync_service import (
    MarketDataSyncService,
    MarketSyncStatus,
    _MARKET_CLOSE_TIME,
)


class MockTradingCalendar:
    def is_trading_day(self, point_date: date) -> bool:
        # Pazartesi - Cuma (0-4)
        return point_date.weekday() < 5


@pytest.fixture
def sync_service(tmp_path):
    duckdb_file = str(tmp_path / "sync_test.duckdb")
    sqlite_file = str(tmp_path / "portfolio_test.db")
    return MarketDataSyncService(
        duckdb_path=duckdb_file,
        sqlite_path=sqlite_file,
        trading_calendar=MockTradingCalendar(),
    )


def test_last_completed_trading_day_before_market_close(sync_service):
    # Çarşamba saat 14:00 -> son tamamlanmış gün Salı olmalı
    wednesday_noon = datetime(2026, 10, 7, 14, 0, 0)
    last_day = sync_service.get_last_completed_trading_day(now=wednesday_noon)
    assert last_day == date(2026, 10, 6)


def test_last_completed_trading_day_after_market_close(sync_service):
    # Çarşamba saat 18:30 -> son tamamlanmış gün Çarşamba olmalı
    wednesday_evening = datetime(2026, 10, 7, 18, 30, 0)
    last_day = sync_service.get_last_completed_trading_day(now=wednesday_evening)
    assert last_day == date(2026, 10, 7)


def test_last_completed_trading_day_on_weekend(sync_service):
    # Pazar günü -> Cuma olmalı
    sunday = datetime(2026, 10, 11, 12, 0, 0)
    last_day = sync_service.get_last_completed_trading_day(now=sunday)
    assert last_day == date(2026, 10, 9)  # Cuma


def test_get_sync_status_empty_db(sync_service):
    wednesday_noon = datetime(2026, 10, 7, 14, 0, 0)
    status = sync_service.get_sync_status(now=wednesday_noon)
    assert status.is_up_to_date is False
    assert status.max_db_date is None


def test_get_sync_status_up_to_date(sync_service):
    # DuckDB'ye sahte tablo ve kayıt ekle
    with sync_service._get_duckdb_conn(read_only=False) as con:
        con.execute("CREATE TABLE bist_stocks (ticker VARCHAR PRIMARY KEY, last_date DATE)")
        con.execute("INSERT INTO bist_stocks VALUES ('THYAO', '2026-10-06')")

    # Çarşamba 14:00 (kapanış öncesi) -> son gün 2026-10-06 -> güncel olmalı!
    wednesday_noon = datetime(2026, 10, 7, 14, 0, 0)
    status = sync_service.get_sync_status(now=wednesday_noon)
    assert status.is_up_to_date is True
    assert len(status.missing_trading_days) == 0


def test_get_sync_status_missing_days(sync_service):
    # DuckDB'de son tarih Cuma (2026-10-02)
    with sync_service._get_duckdb_conn(read_only=False) as con:
        con.execute("CREATE TABLE bist_stocks (ticker VARCHAR PRIMARY KEY, last_date DATE)")
        con.execute("INSERT INTO bist_stocks VALUES ('THYAO', '2026-10-02')")

    # Salı 19:00 -> son gün Salı (2026-10-06) -> Pazartesi ve Salı eksik
    tuesday_evening = datetime(2026, 10, 6, 19, 0, 0)
    status = sync_service.get_sync_status(now=tuesday_evening)
    assert status.is_up_to_date is False
    assert status.missing_trading_days == [date(2026, 10, 5), date(2026, 10, 6)]

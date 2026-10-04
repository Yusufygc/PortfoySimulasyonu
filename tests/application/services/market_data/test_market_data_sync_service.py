from datetime import date, datetime, time as dt_time, timedelta
import pytest
from unittest.mock import MagicMock

from src.application.services.market_data.market_data_sync_service import (
    MarketDataSyncService,
    MarketSyncStatus,
)


class MockTradingCalendar:
    def is_trading_day(self, point_date: date) -> bool:
        # Pazartesi - Cuma (0-4)
        return point_date.weekday() < 5


@pytest.fixture
def sync_service(tmp_path):
    duckdb_file = str(tmp_path / "sync_test.duckdb")
    return MarketDataSyncService(
        duckdb_path=duckdb_file,
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


def test_last_completed_trading_day_waits_for_close_data(sync_service):
    # 18:10 kapanış + 20 dk veri gecikmesi: 18:20'de bugünün barı henüz kesin kapanış değil
    assert sync_service.get_last_completed_trading_day(now=datetime(2026, 10, 7, 18, 20)) == date(2026, 10, 6)
    assert sync_service.get_last_completed_trading_day(now=datetime(2026, 10, 7, 18, 29, 59)) == date(2026, 10, 6)


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


def test_invalid_bar_scan_logs_tickers_and_dates(sync_service, caplog):
    """Tanı: geçersiz kapanışlı bar bulununca hangi hisse/gün olduğu loga yazılır (yeniden indirmenin kaynağını bulmak için)."""
    import duckdb

    con = duckdb.connect(sync_service._duckdb_path)
    con.execute("CREATE TABLE daily_prices (ticker VARCHAR, price_date DATE, open_price DOUBLE, high_price DOUBLE, "
                "low_price DOUBLE, close_price DOUBLE, volume BIGINT)")
    con.execute("INSERT INTO daily_prices VALUES ('AAA', '2026-10-01', 1, 1, 1, NULL, 0), ('BBB', '2026-10-02', 1, 1, 1, 5, 0)")
    con.close()

    with caplog.at_level("WARNING"):
        start = sync_service._find_invalid_bar_start(date(2026, 10, 2))

    assert start == date(2026, 10, 1)
    assert "Geçersiz kapanışlı 1 bar bulundu (ilk 10: AAA 2026-10-01)" in caplog.text

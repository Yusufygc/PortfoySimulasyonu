"""AssetMarketCalendar: sınıf bazlı seans (kripto 7/24, ABD hisse, CME metal vadeli)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.application.services.assets import asset_market_calendar
from src.application.services.assets.asset_market_calendar import AssetMarketCalendar
from src.domain.models.asset import AssetClass


def utc(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


@pytest.fixture
def calendar():
    return AssetMarketCalendar()


# Ocak 2026: New York UTC-5 (kış saati). 5 Ocak pazartesi, 9 Ocak cuma, 10 Ocak cumartesi, 11 Ocak pazar.
@pytest.mark.parametrize(
    "moment,expected",
    [
        (utc(2026, 1, 5, 14, 29), False),   # 09:29 ET
        (utc(2026, 1, 5, 14, 30), True),    # 09:30 ET
        (utc(2026, 1, 5, 20, 59), True),    # 15:59 ET
        (utc(2026, 1, 5, 21, 0), False),    # 16:00 ET
        (utc(2026, 1, 10, 16, 0), False),   # cumartesi
        (utc(2026, 1, 11, 16, 0), False),   # pazar
    ],
)
def test_us_stock_session(calendar, moment, expected):
    assert calendar.is_open(AssetClass.US_STOCK, moment) is expected


@pytest.mark.parametrize(
    "moment,expected",
    [
        (utc(2026, 1, 5, 12, 0), True),     # pazartesi 07:00 ET
        (utc(2026, 1, 5, 22, 30), False),   # pazartesi 17:30 ET günlük mola
        (utc(2026, 1, 5, 23, 0), True),     # pazartesi 18:00 ET mola bitti
        (utc(2026, 1, 9, 21, 59), True),    # cuma 16:59 ET
        (utc(2026, 1, 9, 22, 0), False),    # cuma 17:00 ET hafta kapanışı
        (utc(2026, 1, 10, 12, 0), False),   # cumartesi
        (utc(2026, 1, 11, 22, 59), False),  # pazar 17:59 ET
        (utc(2026, 1, 11, 23, 0), True),    # pazar 18:00 ET açılış
    ],
)
def test_metal_futures_session(calendar, moment, expected):
    assert calendar.is_open(AssetClass.PRECIOUS_METAL, moment) is expected


def test_crypto_is_always_open(calendar):
    assert calendar.is_open(AssetClass.CRYPTO, utc(2026, 1, 10, 3, 0))
    assert calendar.is_open(AssetClass.CRYPTO, utc(2026, 1, 11, 23, 59))


def test_naive_datetime_is_treated_as_utc(calendar):
    assert calendar.is_open(AssetClass.US_STOCK, datetime(2026, 1, 5, 15, 0)) is True


def test_us_market_dst_shift(calendar):
    # Temmuz: New York UTC-4; 13:30 UTC = 09:30 ET açılış
    assert calendar.is_open(AssetClass.US_STOCK, utc(2026, 7, 6, 13, 29)) is False
    assert calendar.is_open(AssetClass.US_STOCK, utc(2026, 7, 6, 13, 30)) is True


def test_sessions_are_always_open_without_timezone_data(monkeypatch):
    monkeypatch.setattr(asset_market_calendar, "_load_new_york", lambda: None)
    calendar = AssetMarketCalendar()

    assert calendar.is_open(AssetClass.US_STOCK, utc(2026, 1, 10, 12, 0)) is True
    assert calendar.is_open(AssetClass.PRECIOUS_METAL, utc(2026, 1, 10, 12, 0)) is True

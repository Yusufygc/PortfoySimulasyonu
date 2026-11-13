"""Piyasa saati: bilgisayar saat diliminden bağımsız Istanbul günü ve saati."""
from __future__ import annotations

from datetime import date, datetime, time, timezone

import pytest

from src.domain import market_clock


def _freeze(monkeypatch, utc_moment: datetime) -> None:
    monkeypatch.setattr(market_clock, "_utc_now", lambda: utc_moment)


def test_market_now_is_istanbul_wall_clock_and_naive(monkeypatch):
    _freeze(monkeypatch, datetime(2026, 10, 4, 9, 30, 15, 123456, tzinfo=timezone.utc))

    now = market_clock.market_now()

    assert now == datetime(2026, 10, 4, 12, 30, 15, 123456)
    assert now.tzinfo is None


def test_market_today_rolls_to_next_day_after_21_utc(monkeypatch):
    _freeze(monkeypatch, datetime(2026, 10, 4, 22, 30, tzinfo=timezone.utc))

    assert market_clock.market_today() == date(2026, 10, 5)


def test_market_time_has_no_microseconds(monkeypatch):
    _freeze(monkeypatch, datetime(2026, 1, 15, 14, 59, 59, 999999, tzinfo=timezone.utc))

    assert market_clock.market_time() == time(17, 59, 59)


def test_fixed_offset_fallback_matches_zoneinfo(monkeypatch):
    zoneinfo_now = market_clock.market_now

    import src.domain.market_clock as clock

    moment = datetime(2026, 7, 1, 20, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(clock, "_utc_now", lambda: moment)
    with_zoneinfo = zoneinfo_now()
    monkeypatch.setattr(clock, "MARKET_TIMEZONE", timezone(clock.timedelta(hours=3)))

    assert clock.market_now() == with_zoneinfo == datetime(2026, 7, 1, 23, 0)

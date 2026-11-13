"""Canlı fiyatın son kapanışın yerine geçme kuralı ve BIST seans penceresi (Istanbul saati, sahte saat)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.application.services.market.bist_market_session_service import BistMarketSessionService
from src.application.services.market.current_price_resolver import SOURCE_DAILY, SOURCE_LIVE, CurrentPriceResolver
from src.domain.live_price_rule import live_price_applies


class _Calendar:
    """Hafta içi işlem günü; 28.10.2026 yarım gün, 29.10.2026 tatil."""

    def is_trading_day(self, day: date) -> bool:
        return day.weekday() < 5 and day != date(2026, 10, 29)

    def is_half_trading_day(self, day: date) -> bool:
        return day == date(2026, 10, 28)


SESSION = BistMarketSessionService(_Calendar())
THURSDAY, FRIDAY, SATURDAY, MONDAY = date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3), date(2026, 10, 5)


def applies(as_of: datetime, last_bar: date | None, now: datetime, source: str = "intraday") -> bool:
    return live_price_applies(source, as_of, last_bar, now, SESSION.session_window)


# ----------------------------- seans penceresi -----------------------------

def test_session_window_full_half_and_closed_days():
    assert SESSION.session_window(FRIDAY) == (datetime(2026, 10, 2, 10, 0), datetime(2026, 10, 2, 18, 30))
    assert SESSION.session_window(date(2026, 10, 28)) == (datetime(2026, 10, 28, 10, 0), datetime(2026, 10, 28, 13, 20))
    assert SESSION.session_window(SATURDAY) is None
    assert SESSION.session_window(date(2026, 10, 29)) is None


@pytest.mark.parametrize(
    "now, expected",
    [
        (datetime(2026, 10, 2, 11, 0), THURSDAY),  # seans içi: dün
        (datetime(2026, 10, 2, 18, 20), THURSDAY),  # kapanış verisi henüz hazır değil
        (datetime(2026, 10, 2, 18, 30), FRIDAY),  # 18:10 + 20 dk
        (datetime(2026, 10, 3, 12, 0), FRIDAY),  # Cumartesi
        (datetime(2026, 10, 5, 0, 30), FRIDAY),  # Pazartesi gece yarısı
        (datetime(2026, 10, 28, 13, 25), date(2026, 10, 28)),  # yarım gün 13:00 + 20 dk
        (datetime(2026, 10, 30, 9, 0), date(2026, 10, 28)),  # tatili (29.10) atlar
    ],
)
def test_last_completed_trading_day(now, expected):
    assert SESSION.last_completed_trading_day(now) == expected


# ----------------------------- kural -----------------------------

def test_in_session_live_price_on_new_day_applies():
    assert applies(datetime(2026, 10, 5, 11, 0), FRIDAY, now=datetime(2026, 10, 5, 11, 5))


def test_live_price_taken_outside_session_never_applies():
    """Gece/hafta sonu/seans öncesi kayıt son kapanıştır; yeni gün sayılırsa günlük değişim %0 olurdu."""
    assert not applies(datetime(2026, 10, 5, 0, 47), FRIDAY, now=datetime(2026, 10, 5, 0, 50))  # gece
    assert not applies(datetime(2026, 10, 3, 14, 0), FRIDAY, now=datetime(2026, 10, 3, 14, 0))  # Cumartesi
    assert not applies(datetime(2026, 10, 5, 9, 30), FRIDAY, now=datetime(2026, 10, 5, 9, 31))  # seans öncesi
    assert not applies(datetime(2026, 10, 2, 19, 0), THURSDAY, now=datetime(2026, 10, 2, 19, 0))  # kapanış sonrası


def test_same_day_bar_wins_once_close_data_is_ready():
    as_of = datetime(2026, 10, 2, 17, 55)
    assert applies(as_of, FRIDAY, now=datetime(2026, 10, 2, 18, 0))  # o günün barı kısmi olabilir: canlı
    assert not applies(as_of, FRIDAY, now=datetime(2026, 10, 2, 18, 30))  # kesin kapanış barı
    assert not applies(as_of, FRIDAY, now=datetime(2026, 10, 5, 11, 0))


def test_live_price_older_than_last_bar_or_not_intraday_never_applies():
    assert not applies(datetime(2026, 10, 1, 15, 0), FRIDAY, now=datetime(2026, 10, 2, 19, 0))
    assert not applies(datetime(2026, 10, 5, 11, 0), FRIDAY, now=datetime(2026, 10, 5, 11, 0), source="last_close")


def test_live_price_without_bars_applies_only_in_session():
    assert applies(datetime(2026, 10, 5, 11, 0), None, now=datetime(2026, 10, 5, 11, 0))
    assert not applies(datetime(2026, 10, 4, 11, 0), None, now=datetime(2026, 10, 4, 11, 0))


# ----------------------------- resolver: gece açılışı -----------------------------

class _LatestRepo:
    def __init__(self, rows):
        self.rows = rows

    def get_latest_prices(self, ids):
        return {sid: self.rows[sid] for sid in ids if sid in self.rows}


class _PriceRepo:
    def __init__(self, bars):
        self.bars = bars

    def get_latest_price_dates(self, ids):
        return {sid: max(self.bars[sid]) for sid in ids if self.bars.get(sid)}

    def get_price_for_date(self, sid, day):
        close = self.bars.get(sid, {}).get(day)
        return SimpleNamespace(close_price=Decimal(close)) if close is not None else None

    def get_last_price_before(self, sid, day):
        earlier = [d for d in self.bars.get(sid, {}) if d <= day]
        return SimpleNamespace(close_price=Decimal(self.bars[sid][max(earlier)])) if earlier else None


def test_resolver_ignores_night_snapshot_and_keeps_real_daily_change(monkeypatch):
    """Pazartesi 00:47'de çekilen kayıt (UTC 21:47 Pazar) Cuma kapanışıdır: değişim Perşembe->Cuma olmalı (%10)."""
    from src.application.services.market import current_price_resolver as module

    night_utc = datetime(2026, 10, 4, 21, 47)  # naive = UTC; Istanbul 05.10 00:47
    live = SimpleNamespace(price=Decimal("11"), as_of=night_utc, source="intraday")
    resolver = CurrentPriceResolver(
        _LatestRepo({1: live}),
        _PriceRepo({1: {THURSDAY: "10", FRIDAY: "11"}}),
        session_service=SESSION,
    )
    monkeypatch.setattr(module, "market_now", lambda: datetime(2026, 10, 5, 0, 50))

    resolved = resolver.resolve([1])[1]

    assert resolved.source == SOURCE_DAILY and resolved.price_date == FRIDAY
    assert resolver.daily_change_pct(1, resolved) == Decimal("10")


def test_resolver_uses_in_session_live_price(monkeypatch):
    from src.application.services.market import current_price_resolver as module

    live = SimpleNamespace(price=Decimal("12.1"), as_of=datetime(2026, 10, 5, 8, 0), source="intraday")  # 11:00 TR
    resolver = CurrentPriceResolver(_LatestRepo({1: live}), _PriceRepo({1: {FRIDAY: "11"}}), session_service=SESSION)
    monkeypatch.setattr(module, "market_now", lambda: datetime(2026, 10, 5, 11, 5))

    resolved = resolver.resolve([1])[1]

    assert resolved.source == SOURCE_LIVE and resolved.price_date == MONDAY
    assert resolver.daily_change_pct(1, resolved) == Decimal("10")

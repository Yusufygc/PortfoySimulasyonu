"""İzleme listesi canlı fiyat bindirmesi, canlı yenileme kapsamı/zaman bütçesi ve takılan yenilemenin serbest bırakılması."""
from __future__ import annotations

import time
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QSettings

from src.application.services.market.live_price_refresh_service import LivePriceRefreshService
from src.domain.market_clock import to_market_date
from src.ui_qml.controllers import system_controller
from src.ui_qml.controllers import watchlist_pricing as pricing
from src.ui_qml.controllers.system_controller import SystemController


def _bar(day: date, close: float, low: float | None = None, high: float | None = None, volume: float | None = None):
    return SimpleNamespace(price_date=day, close_price=Decimal(str(close)), low_price=None if low is None else Decimal(str(low)),
                           high_price=None if high is None else Decimal(str(high)), volume=volume)


FRIDAY, MONDAY = date(2026, 10, 2), date(2026, 10, 5)
BARS = [_bar(date(2026, 10, 1), 10.0), _bar(FRIDAY, 11.0, low=10.5, high=11.5, volume=2_500_000)]


# ----------------------------- fiyat bindirme -----------------------------

def test_bars_only_pricing_uses_last_two_closes():
    row = pricing.price_from_bars(BARS)
    assert row.price == 11.0
    assert row.daily_diff_pct == pytest.approx(10.0)
    assert (row.day_low, row.day_high, row.volume_text) == (10.5, 11.5, "2.5M")
    assert row.sparkline == [10.0, 11.0]


def test_live_price_on_new_session_day_compares_with_last_close():
    row = pricing.price_row(BARS, 12.1, MONDAY)
    assert row.price == 12.1
    assert row.daily_diff_pct == pytest.approx(10.0)  # 11.0 -> 12.1
    assert row.day_high == 12.1 and row.day_low == 10.5
    assert row.sparkline == [10.0, 11.0, 12.1]


def test_live_price_same_day_as_last_bar_replaces_that_bar():
    row = pricing.price_row(BARS, 10.5, FRIDAY)
    assert row.daily_diff_pct == pytest.approx(5.0)  # önceki kapanış 10.0
    assert row.sparkline == [10.0, 10.5]


def test_no_applicable_live_price_uses_bars():
    assert pricing.price_row(BARS, None, None).price == 11.0


def test_live_price_without_bars_still_prices_row():
    row = pricing.price_row([], 5.0, MONDAY)
    assert row.price == 5.0 and row.daily_diff_pct == 0.0
    assert pricing.price_row([], None, None) is None


def test_to_market_date_converts_utc_to_istanbul_day():
    assert to_market_date(datetime(2026, 10, 4, 22, 30, tzinfo=timezone.utc)) == date(2026, 10, 5)  # UTC+3
    assert to_market_date(datetime(2026, 10, 5, 9, 0)) == date(2026, 10, 5)  # naive = UTC


# ----------------------------- canlı yenileme kapsamı -----------------------------

class _HealthService:
    def active_stock_ids(self, scope=None):
        return {1, 2}


class _StockRepo:
    def get_ticker_map_for_stock_ids(self, ids):
        return {i: f"T{i}" for i in ids}


class _Lookup:
    def __init__(self, delay: float = 0.0):
        self.calls, self.delay = [], delay

    def lookup_price_for_ticker(self, ticker):
        self.calls.append(ticker)
        time.sleep(self.delay)
        return SimpleNamespace(price=Decimal("1.5"), as_of=datetime.now(timezone.utc), source="intraday")


def test_live_refresh_includes_extra_watchlist_stocks():
    lookup = _Lookup()
    service = LivePriceRefreshService(_StockRepo(), lookup, _HealthService(), extra_stock_ids_provider=lambda: {2, 7})
    result = service.refresh_active_prices()
    assert sorted(lookup.calls) == ["T1", "T2", "T7"]
    assert set(result.prices) == {1, 2, 7}


def test_live_refresh_survives_failing_extra_provider():
    def broken():
        raise RuntimeError("kaynak yok")

    service = LivePriceRefreshService(_StockRepo(), _Lookup(), _HealthService(), extra_stock_ids_provider=broken)
    assert set(service.refresh_active_prices().prices) == {1, 2}


def test_live_refresh_stops_when_time_budget_is_exhausted():
    lookup = _Lookup(delay=0.05)
    service = LivePriceRefreshService(_StockRepo(), lookup, _HealthService())
    service.time_budget_seconds = 0.01
    result = service.refresh_active_prices()
    assert len(lookup.calls) < 2
    assert any("Zaman bütçesi doldu" in e for e in result.errors)


# ----------------------------- takılan yenileme -----------------------------

@pytest.fixture
def system(qapp, tmp_path):
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    container = SimpleNamespace(
        live_price_refresh_service=SimpleNamespace(refresh_active_prices=lambda: SimpleNamespace(prices={}, updated_count=0)),
        bist_market_session_service=SimpleNamespace(status_for=lambda day, at=None: SimpleNamespace(is_open=True)),
        event_bus=None,
    )
    return SystemController(container=container, settings=settings, autostart=False)


def test_stalled_refresh_is_released_and_new_refresh_starts(system, monkeypatch):
    system._is_refreshing = True
    system._refresh_started = time.monotonic() - system_controller._REFRESH_STALL_SECONDS - 1
    old_executor = system._executor
    started = []
    monkeypatch.setattr(system._executor.__class__, "submit", lambda self, fn: started.append(fn))
    system.refreshNow()
    assert system._refresh_generation == 1
    assert system._executor is not old_executor
    assert system._is_refreshing is True and len(started) == 1  # yeni yenileme başladı


def test_recent_refresh_is_not_interrupted(system):
    system._is_refreshing = True
    system._refresh_started = time.monotonic()
    old_executor = system._executor
    system.refreshNow()
    assert system._executor is old_executor and system._refresh_generation == 0


def test_session_check_passes_market_time(system, monkeypatch):
    seen = []
    system._container.bist_market_session_service = SimpleNamespace(
        status_for=lambda day, at=None: seen.append(at) or SimpleNamespace(is_open=False))
    assert system.session_open() is False
    assert seen and seen[0] is not None

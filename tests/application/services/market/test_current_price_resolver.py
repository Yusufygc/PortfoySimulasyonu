from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from src.application.services.market.current_price_resolver import (
    SOURCE_DAILY,
    SOURCE_LIVE,
    CurrentPriceResolver,
)
from src.domain.models.latest_price import LatestPrice


class FakeLatestRepo:
    def __init__(self, rows):
        self.rows = rows

    def get_latest_prices(self, ids):
        return {sid: self.rows[sid] for sid in ids if sid in self.rows}


class FakePriceRepo:
    """bars: {stock_id: {date: close}}"""

    def __init__(self, bars):
        self.bars = bars

    def get_latest_price_dates(self, ids):
        return {sid: max(self.bars[sid]) for sid in ids if self.bars.get(sid)}

    def get_price_for_date(self, sid, d):
        close = self.bars.get(sid, {}).get(d)
        return SimpleNamespace(close_price=Decimal(str(close))) if close is not None else None

    def get_last_price_before(self, sid, d):
        earlier = [day for day in self.bars.get(sid, {}) if day <= d]  # gerçek repo gibi: verilen gün dahil
        if not earlier:
            return None
        return SimpleNamespace(close_price=Decimal(str(self.bars[sid][max(earlier)])))


def live(sid, price, as_of):
    return LatestPrice(None, sid, Decimal(str(price)), as_of, "intraday", "t", as_of)


def test_stale_live_price_loses_to_newer_daily_close():
    """Canlı fiyat 11 Eylül'den, kapanışlar 1 Ekim'e kadar: kapanış kullanılmalı, değişim anlamlı olmalı."""
    resolver = CurrentPriceResolver(
        FakeLatestRepo({1: live(1, "1.21", datetime(2026, 9, 11, 15, 0))}),
        FakePriceRepo({1: {date(2026, 9, 30): "0.92", date(2026, 10, 1): "0.96"}}),
    )

    resolved = resolver.resolve([1])[1]

    assert resolved.source == SOURCE_DAILY and resolved.price == Decimal("0.96")
    assert resolved.price_date == date(2026, 10, 1)
    # önceki kapanış 30 Eylül (1 Ekim'den önceki), bugünden önceki değil
    assert resolver.previous_close(1, resolved) == Decimal("0.92")
    assert round(resolver.daily_change_pct(1, resolved), 2) == Decimal("4.35")


def test_live_price_wins_when_newer_than_last_close():
    resolver = CurrentPriceResolver(
        FakeLatestRepo({1: live(1, "10.5", datetime(2026, 10, 2, 11, 0))}),
        FakePriceRepo({1: {date(2026, 10, 1): "10.0"}}),
    )

    resolved = resolver.resolve([1])[1]

    assert resolved.source == SOURCE_LIVE and resolved.price == Decimal("10.5")
    assert resolver.daily_change_pct(1, resolved) == Decimal("5")


def test_same_day_daily_close_beats_live_snapshot():
    resolver = CurrentPriceResolver(
        FakeLatestRepo({1: live(1, "10.4", datetime(2026, 10, 2, 17, 50))}),
        FakePriceRepo({1: {date(2026, 10, 1): "10.0", date(2026, 10, 2): "10.6"}}),
    )

    resolved = resolver.resolve([1])[1]

    assert resolved.source == SOURCE_DAILY and resolved.price == Decimal("10.6")
    assert resolver.previous_close(1, resolved) == Decimal("10.0")


def test_missing_sources_fall_back_gracefully():
    only_live = CurrentPriceResolver(FakeLatestRepo({1: live(1, "5", datetime(2026, 9, 1))}), FakePriceRepo({}))
    assert only_live.resolve([1])[1].source == SOURCE_LIVE

    only_daily = CurrentPriceResolver(FakeLatestRepo({}), FakePriceRepo({2: {date(2026, 10, 1): "7"}}))
    assert only_daily.price_map([2]) == {2: Decimal("7")}
    assert only_daily.daily_change_pct(2, only_daily.resolve([2])[2]) is None  # önceki kapanış yok

    nothing = CurrentPriceResolver(FakeLatestRepo({}), FakePriceRepo({}))
    assert nothing.resolve([3]) == {} and nothing.resolve([]) == {}


def test_resolver_survives_repository_errors():
    class Broken:
        def get_latest_prices(self, ids):
            raise RuntimeError("db")

        def get_latest_price_dates(self, ids):
            raise RuntimeError("db")

    assert CurrentPriceResolver(Broken(), Broken()).resolve([1]) == {}

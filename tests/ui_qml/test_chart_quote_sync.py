"""Grafik başlığı (hisse adı, fiyat, değişim) hisse değişince anında güncellenir; canlı fiyat ve fiyat yenilemesi grafiğe yansır."""
from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from src.application.services.market.current_price_resolver import ResolvedPrice
from src.ui_qml.app import wire_controllers
from src.ui_qml.controllers.chart_candle_sources import overlay_live_price
from src.ui_qml.controllers.chart_controller import ChartController

DAY0 = date(2026, 10, 26)  # pazartesi


def _bars(closes):
    return [
        SimpleNamespace(price_date=DAY0 + timedelta(days=i), open_price=c, high_price=c + 1, low_price=c - 1,
                        close_price=c, volume=1000)
        for i, c in enumerate(closes)
    ]


class _Lookup:
    def __init__(self, series, live_stock=None):
        self._series = series
        self._live_stock = live_stock

    def get_market_bars(self, ticker, start, end):
        return self._series.get(ticker, [])

    def get_market_company_name(self, ticker):
        return f"{ticker} A.Ş."

    def find_stock(self, ticker):
        return self._live_stock

    def get_price_series(self, stock_id, start, end):
        return []

    def list_market_tickers(self):
        return list(self._series)


def _controller(series, resolver=None, live_stock=None):
    container = SimpleNamespace(stock_lookup_service=_Lookup(series, live_stock), asset_chart_service=None,
                                current_price_resolver=resolver)
    return ChartController(container=container)


def test_quote_is_final_when_quote_changed_is_emitted():
    controller = _controller({"AAA": _bars([10, 11]), "BBB": _bars([200, 190])})
    controller.loadTicker("AAA")
    seen = []
    controller.quoteChanged.connect(lambda: seen.append((controller.companyName, controller.lastPrice, controller.priceChange)))
    controller.loadTicker("BBB")
    assert seen == [("BBB A.Ş.", "₺190,00", "-%5,00")]
    assert controller.isPositive is False and controller.hasQuote


def test_no_data_resets_quote_instead_of_keeping_previous_symbol_price():
    controller = _controller({"AAA": _bars([10, 11])})
    controller.loadTicker("AAA")
    assert controller.hasQuote and controller.lastPrice == "₺11,00"
    controller.loadTicker("ZZZ")
    assert not controller.hasQuote
    assert controller.lastPrice == "₺0,00" and controller.priceChange == "%0,00"


def test_daily_change_is_shown_for_every_timeframe():
    controller = _controller({"AAA": _bars([10, 11, 12, 13, 14, 15, 16, 20])})
    controller.loadTicker("AAA")
    daily = (controller.lastPrice, controller.priceChange)
    controller.setTimeframe("1W")
    assert (controller.lastPrice, controller.priceChange) == daily == ("₺20,00", "+%25,00")


def test_overlay_updates_same_day_appends_new_day_and_ignores_older():
    candles = [{"time": "2026-10-26", "open": 10, "high": 12, "low": 9, "close": 11}]
    volumes = [{"time": "2026-10-26", "value": 5.0, "color": "x"}]
    overlay_live_price(candles, volumes, 13.0, date(2026, 10, 26))
    assert candles[0]["close"] == 13.0 and candles[0]["high"] == 13.0 and len(candles) == 1
    overlay_live_price(candles, volumes, 8.0, date(2026, 10, 26))
    assert candles[0]["close"] == 8.0 and candles[0]["low"] == 8.0
    overlay_live_price(candles, volumes, 9.5, date(2026, 10, 27))
    assert [c["time"] for c in candles] == ["2026-10-26", "2026-10-27"]
    assert candles[1]["open"] == 8.0 and candles[1]["close"] == 9.5 and len(volumes) == 2
    overlay_live_price(candles, volumes, 99.0, date(2026, 10, 20))
    assert len(candles) == 2


class _Resolver:
    def __init__(self, source="live", price="12.5", price_date=DAY0 + timedelta(days=2)):
        self.resolved = ResolvedPrice(Decimal(price), price_date, source)

    def resolve(self, ids):
        return {i: self.resolved for i in ids}


def test_live_price_moves_last_candle_header_and_payload():
    controller = _controller({"AAA": _bars([10, 11])}, _Resolver(), live_stock=SimpleNamespace(id=7))
    events = []
    controller.chartDataLoaded.connect(lambda t, payload: events.append(json.loads(payload)))
    controller.loadTicker("AAA")
    candles = events[-1]["candles"]
    assert candles[-1]["time"] == "2026-10-28" and candles[-1]["close"] == 12.5
    assert controller.lastPrice == "₺12,50" and controller.priceChange == "+%13,64"


def test_daily_source_and_unknown_stock_leave_candles_untouched():
    for resolver, stock in ((_Resolver(source="daily"), SimpleNamespace(id=7)), (_Resolver(), None)):
        controller = _controller({"AAA": _bars([10, 11])}, resolver, live_stock=stock)
        controller.loadTicker("AAA")
        assert controller.lastPrice == "₺11,00"


def test_reload_current_refetches_with_new_live_price_without_ticker_change():
    resolver = _Resolver(price="12.5")
    controller = _controller({"AAA": _bars([10, 11])}, resolver, live_stock=SimpleNamespace(id=7))
    controller.loadTicker("AAA")
    ticker_events, data_events = [], []
    controller.tickerChanged.connect(ticker_events.append)
    controller.chartDataLoaded.connect(lambda t, payload: data_events.append(json.loads(payload)))
    resolver.resolved = ResolvedPrice(Decimal("14"), DAY0 + timedelta(days=2), "live")
    controller.reloadCurrent()
    assert ticker_events == [] and data_events[-1]["candles"][-1]["close"] == 14.0
    assert controller.lastPrice == "₺14,00"


class _Noop:
    """Her özelliği ve çağrıyı yutan taslak: `wire_controllers` yalnızca bağlantı kurar."""

    def __getattr__(self, name):
        return _Noop()

    def __call__(self, *args, **kwargs):
        return None


class _FakeSignal:
    def __init__(self):
        self.targets = []

    def connect(self, target):
        self.targets.append(target)

    def emit(self):
        for target in list(self.targets):
            target()


class _Refresh(_Noop):
    def __init__(self):
        self.pricesChanged = _FakeSignal()


class _Controllers(dict):
    def __missing__(self, key):
        return _Noop()


def test_prices_changed_signal_reloads_chart():
    chart = _controller({"AAA": _bars([10, 11])})
    chart.loadTicker("AAA")
    refresh = _Refresh()
    controllers = _Controllers(chartController=chart, priceRefreshController=refresh)
    wire_controllers(controllers)
    events = []
    chart.chartDataLoaded.connect(lambda t, payload: events.append(t))
    refresh.pricesChanged.emit()
    assert events == ["AAA"]

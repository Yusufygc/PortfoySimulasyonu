"""`ChartController._fetch_and_emit_chart_data` karakterizasyon testi: veri kaynağı sırası, mum/hacim üretimi,
yeniden örnekleme, son fiyat metinleri ve JSON paketi refaktörden önce/sonra aynı kalmalı.

Beklenen çıktılar `golden/chart_fetch_golden.json` dosyasındadır (refaktör öncesi koddan üretildi): okunabilir özet
alanları ve tüm paketin SHA-256 özeti. Gerçek veritabanı yoktur; arama servisi sahtedir.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.ui_qml.controllers.chart_controller import ChartController

GOLDEN_PATH = Path(__file__).parent / "golden" / "chart_fetch_golden.json"


def _weekdays(count: int, start: date = date(2026, 1, 5)) -> list[date]:
    days, current = [], start
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def _close(index: int) -> float:
    return round(100 + index * 0.5 + (index % 5) * 0.3, 4)


def _duckdb_bars() -> list[SimpleNamespace]:
    bars = []
    for i, day in enumerate(_weekdays(70)):
        close = _close(i)
        complete = i % 3 != 0  # her üçüncü barda açılış/yüksek/düşük eksik
        bars.append(SimpleNamespace(
            price_date=day,
            close_price=close,
            open_price=close - 0.4 if complete else 0,
            high_price=close + 0.9 if complete else None,
            low_price=close - 1.1 if complete else 0,
            volume=1000 + i * 10 if i % 4 else None,
        ))
    return bars


def _sqlite_prices() -> list[SimpleNamespace]:
    prices = []
    for i, day in enumerate(_weekdays(70)):
        close = _close(i)
        full = i % 2 == 0
        prices.append(SimpleNamespace(
            price_date=day,
            close_price=close,
            open_price=close - 0.3 if full else None,
            high_price=close + 0.8 if full else None,
            low_price=close - 0.9 if full else None,
            volume=(500 + i) if i % 5 else None,
        ))
    return list(reversed(prices))  # kod tarihe göre sıralıyor


class _Lookup:
    def __init__(self, bars=None, bars_error=False, stock=None, prices=None, name="Test Şirketi A.Ş."):
        self._bars, self._bars_error, self._stock, self._prices, self._name = bars, bars_error, stock, prices, name

    def get_market_bars(self, ticker, start, end):
        if self._bars_error:
            raise RuntimeError("duckdb yok")
        return self._bars

    def get_market_company_name(self, ticker):
        return self._name

    def find_stock(self, ticker):
        return self._stock

    def get_price_series(self, stock_id, start, end):
        return self._prices


def _container(**kwargs):
    return SimpleNamespace(stock_lookup_service=_Lookup(**kwargs))


_STOCK = SimpleNamespace(id=7, ticker="TEST.IS", name="Test Hisse.IS")

# senaryo adı -> (container üretici, zaman dilimi, ortalama maliyet)
SCENARIOS = {
    "duckdb_daily": (lambda: _container(bars=_duckdb_bars()), "1D", None),
    "duckdb_weekly_with_cost": (lambda: _container(bars=_duckdb_bars()), "1W", 104.5),
    "duckdb_monthly": (lambda: _container(bars=_duckdb_bars()), "1M", None),
    "sqlite_fallback_after_duckdb_error": (
        lambda: _container(bars_error=True, stock=_STOCK, prices=_sqlite_prices()), "1D", None),
    "sqlite_fallback_when_duckdb_empty": (
        lambda: _container(bars=[], stock=_STOCK, prices=_sqlite_prices()), "1W", None),
    "no_data_anywhere": (lambda: _container(bars=[], stock=None, prices=None), "1D", None),
}


def run_scenario(name: str) -> dict:
    make_container, timeframe, average_cost = SCENARIOS[name]
    controller = ChartController(container=make_container())
    controller._current_timeframe = timeframe
    if average_cost:
        controller._average_cost, controller._average_cost_ticker = average_cost, "TEST"
    events: list[tuple[str, str]] = []
    controller.chartDataLoaded.connect(lambda ticker, payload: events.append((ticker, payload)))

    controller._fetch_and_emit_chart_data("TEST.IS")

    assert len(events) == 1
    ticker, raw = events[0]
    payload = json.loads(raw)
    candles, volumes = payload["candles"], payload["volumes"]
    return {
        "emitted_ticker": ticker,
        "payload_keys": sorted(payload),
        "ticker": payload["ticker"],
        "companyName": payload["companyName"],
        "timeframe": payload["timeframe"],
        "avgCost": payload["avgCost"],
        "candle_count": len(candles),
        "first_candle": candles[0] if candles else None,
        "last_candle": candles[-1] if candles else None,
        "first_volume": volumes[0] if volumes else None,
        "last_volume": volumes[-1] if volumes else None,
        "controller_state": [controller.lastPrice, controller.priceChange, controller.isPositive, controller.companyName],
        "payload_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest(),
    }


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_fetch_and_emit_output_is_unchanged(name):
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert json.loads(json.dumps(run_scenario(name))) == golden[name]


def test_offline_mode_without_container_emits_demo_candles():
    controller = ChartController(container=None)
    events: list[tuple[str, str]] = []
    controller.chartDataLoaded.connect(lambda ticker, payload: events.append((ticker, payload)))

    controller._fetch_and_emit_chart_data("THYAO")

    payload = json.loads(events[0][1])
    assert len(payload["candles"]) > 100
    assert {"time", "open", "high", "low", "close"} <= set(payload["candles"][0])
    assert len(payload["volumes"]) == len(payload["candles"])

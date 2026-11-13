"""Düşük fiyatlı hisselerde grafik mumu ve gösterge hassasiyeti (2 hane yuvarlama 0,17 / MACD 0,00 üretiyordu)."""
from datetime import date, timedelta

from src.ui_qml.controllers.chart_candle_sources import _candle, overlay_live_price, price_digits
from src.ui_qml.controllers.chart_indicators import calculate_indicators


def test_price_digits_by_level():
    assert price_digits(105.4) == 2 and price_digits(10) == 2
    assert price_digits(2.1128) == 4 and price_digits(0.1691) == 4


def test_low_price_candle_keeps_four_digits():
    candle = _candle("2016-07-01", 0.1691, 0.1731, 0.1650, 0.1691)
    assert (candle["open"], candle["high"], candle["low"], candle["close"]) == (0.1691, 0.1731, 0.165, 0.1691)
    assert _candle("2026-01-05", 105.456, 106.0, 104.0, 105.456)["close"] == 105.46


def test_live_overlay_keeps_low_price_precision():
    candles = [_candle("2026-11-06", 1.21, 1.23, 1.20, 1.2150)]
    volumes = [{"time": "2026-11-06", "value": 0}]
    overlay_live_price(candles, volumes, 1.2345, date(2026, 11, 6))
    assert candles[-1]["close"] == 1.2345


def test_macd_of_low_priced_stock_is_not_flattened():
    start = date(2025, 1, 1)
    closes = [1.5 + 0.2 * ((i % 20) / 20) + i * 0.002 for i in range(80)]
    candles = [_candle((start + timedelta(days=i)).isoformat(), c, c + 0.01, c - 0.01, c) for i, c in enumerate(closes)]
    hist = [p["value"] for p in calculate_indicators(candles)["macd"]["hist"]]
    assert any(0 < abs(v) < 0.005 for v in hist)  # 2 haneye yuvarlansaydı 0,00 olurdu

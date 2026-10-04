"""Grafik teknik indikatör serileri ve Golden/Death Cross işaretçileri (saf fonksiyonlar).

`ChartController` mumları buraya verir; çıktı Lightweight Charts'ın beklediği `{time, value}` serileri ve
işaretçi listesidir.
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from src.application.services.analysis.technical.golden_cross import CrossType, detect_crosses
from src.application.services.analysis.technical.indicators import bollinger_bands, ema, macd, rsi, sma

logger = logging.getLogger(__name__)

_GOLDEN_MARKER = {"position": "belowBar", "color": "#089981", "shape": "arrowUp", "text": "Golden Cross"}
_DEATH_MARKER = {"position": "aboveBar", "color": "#f23645", "shape": "arrowDown", "text": "Death Cross"}
_HIST_UP_COLOR = "rgba(8, 153, 129, 0.7)"
_HIST_DOWN_COLOR = "rgba(242, 54, 69, 0.7)"


def empty_indicators() -> dict[str, Any]:
    return {
        "sma20": [],
        "sma50": [],
        "sma200": [],
        "ema20": [],
        "bb": {"upper": [], "middle": [], "lower": []},
        "rsi": [],
        "macd": {"macd": [], "signal": [], "hist": []},
        "markers": [],
    }


def to_line_data(series: pd.Series) -> list[dict[str, Any]]:
    return [{"time": str(t), "value": round(float(v), 2)} for t, v in series.dropna().items()]


def _histogram_data(hist: pd.Series) -> list[dict[str, Any]]:
    return [
        {
            "time": str(t),
            "value": round(float(v), 2),
            "color": _HIST_UP_COLOR if v >= 0 else _HIST_DOWN_COLOR,
        }
        for t, v in hist.dropna().items()
    ]


def _marker(time: Any, template: dict[str, str]) -> dict[str, str]:
    return {"time": str(time), **template}


def _markers_from_events(events) -> list[dict[str, str]]:
    templates = {CrossType.GOLDEN: _GOLDEN_MARKER, CrossType.DEATH: _DEATH_MARKER}
    return [_marker(ev.cross_date, templates[ev.cross_type]) for ev in events if ev.cross_type in templates]


def _markers_from_sma_difference(s50: pd.Series, s200: pd.Series) -> list[dict[str, str]]:
    """Kısa vadeli seriler için yedek: SMA50 - SMA200 farkının işaret değiştirdiği günler."""
    if s50.dropna().empty or s200.dropna().empty:
        return []
    diff = (s50 - s200).dropna()
    if len(diff) <= 1:
        return []
    markers: list[dict[str, str]] = []
    prev_val = diff.iloc[0]
    for time, curr_val in diff.iloc[1:].items():
        if prev_val < 0 and curr_val >= 0:
            markers.append(_marker(time, _GOLDEN_MARKER))
        elif prev_val > 0 and curr_val <= 0:
            markers.append(_marker(time, _DEATH_MARKER))
        prev_val = curr_val
    return markers


def cross_markers(closes: pd.Series, s50: pd.Series, s200: pd.Series) -> list[dict[str, str]]:
    """Golden/Death Cross işaretçileri: önce uygulama servisi, olay yoksa SMA farkı yedeği."""
    try:
        markers = _markers_from_events(detect_crosses(closes, short=50, long=200))
        return markers or _markers_from_sma_difference(s50, s200)
    except Exception as exc:
        logger.debug("Golden/Death cross tespiti sirasinda istisna: %s", exc)
        return []


def calculate_indicators(candles: list[dict[str, Any]]) -> dict[str, Any]:
    """SMA/EMA, Bollinger, RSI, MACD serilerini ve Golden/Death Cross işaretçilerini hesaplar."""
    if not candles:
        return empty_indicators()

    times = [c["time"] for c in candles]
    closes = pd.Series([c["close"] for c in candles], index=times)
    s20, s50, s200 = sma(closes, 20), sma(closes, 50), sma(closes, 200)
    bb_upper, bb_mid, bb_lower = bollinger_bands(closes, 20, 2.0)
    macd_line, signal_line, hist_line = macd(closes, 12, 26, 9)

    return {
        "sma20": to_line_data(s20),
        "sma50": to_line_data(s50),
        "sma200": to_line_data(s200),
        "ema20": to_line_data(ema(closes, 20)),
        "bb": {
            "upper": to_line_data(bb_upper),
            "middle": to_line_data(bb_mid),
            "lower": to_line_data(bb_lower),
        },
        "rsi": to_line_data(rsi(closes, 14)),
        "macd": {
            "macd": to_line_data(macd_line),
            "signal": to_line_data(signal_line),
            "hist": _histogram_data(hist_line),
        },
        "markers": cross_markers(closes, s50, s200),
    }

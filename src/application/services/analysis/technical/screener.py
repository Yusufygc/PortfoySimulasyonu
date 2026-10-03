"""
BIST Çoklu Sinyal Tarayıcısı — saf indikatör anlık görüntüsü (snapshot) ve filtreler.

Ağsız, durumsuz, IO yok — saf fonksiyonlar (golden_cross.py ile aynı desen).
DB erişimi ve orkestrasyon `screener_service.py`'dedir.

Hazır filtreler (bkz. TRANSFORMATION_PLAN.md §3.1):
- rsi_oversold_above_ema200: RSI < 30 (aşırı satım) + Fiyat > EMA200
- macd_bullish_cross_volume_spike: MACD bullish kesişim + Hacim > 20 günlük ortalama
- bollinger_lower_band_touch: Fiyat, Bollinger alt bandına değmiş/altına inmiş
- adx_strong_uptrend: ADX > 25 ve +DI > -DI (güçlü yükseliş trendi)
- supertrend_buy_signal: Supertrend son barda düşüşten yükselişe döndü

ADX ve Supertrend High/Low serisi gerektirir; yalnızca kapanışı olan hisselerde bu filtreler eşleşmez.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, NamedTuple, Optional

import pandas as pd

from src.application.services.analysis.technical.indicators import (
    bollinger_bands,
    adx,
    ema,
    macd,
    rsi,
    sma,
    supertrend,
)

_RSI_PERIOD = 14
_EMA_TREND_PERIOD = 200
_MACD_FAST, _MACD_SLOW, _MACD_SIGNAL = 12, 26, 9
_BOLLINGER_PERIOD, _BOLLINGER_STD = 20, 2.0
_VOLUME_SMA_PERIOD = 20
_RSI_OVERSOLD_THRESHOLD = 30.0
_ADX_PERIOD = 14
_ADX_STRONG_TREND = 25.0
_SUPERTREND_PERIOD, _SUPERTREND_MULTIPLIER = 10, 3.0


@dataclass(frozen=True)
class IndicatorSnapshot:
    """Bir hissenin son barına ait indikatör değerleri. Yetersiz ısınma (warmup) → None."""
    close: float
    rsi14: Optional[float]
    ema200: Optional[float]
    macd_line: Optional[float]
    macd_signal: Optional[float]
    macd_line_prev: Optional[float]
    macd_signal_prev: Optional[float]
    volume: Optional[float]
    volume_sma20: Optional[float]
    bb_lower: Optional[float]
    bb_upper: Optional[float] = None
    adx14: Optional[float] = None
    plus_di14: Optional[float] = None
    minus_di14: Optional[float] = None
    supertrend_direction: Optional[int] = None
    supertrend_direction_prev: Optional[int] = None


def _safe_float(value) -> Optional[float]:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _direction_or_none(series: pd.Series, offset: int) -> Optional[int]:
    """Supertrend yönü (+1/-1); ısınma (0) veya yetersiz bar için None."""
    if len(series) < offset:
        return None
    value = int(series.iloc[-offset])
    return value if value != 0 else None


def build_snapshot(
    closes: pd.Series,
    highs: pd.Series,
    lows: pd.Series,
    volumes: pd.Series,
) -> Optional[IndicatorSnapshot]:
    """Son bar için indikatör anlık görüntüsü üretir."""
    if len(closes) == 0 or pd.isna(closes.iloc[-1]):
        return None

    rsi_series = rsi(closes, period=_RSI_PERIOD)
    ema_series = ema(closes, period=_EMA_TREND_PERIOD)
    macd_line, macd_signal, _ = macd(closes, _MACD_FAST, _MACD_SLOW, _MACD_SIGNAL)
    bb_upper, _, bb_lower = bollinger_bands(closes, period=_BOLLINGER_PERIOD, num_std=_BOLLINGER_STD)
    volume_sma = sma(volumes, period=_VOLUME_SMA_PERIOD) if len(volumes) else pd.Series(dtype=float)

    has_ohlc = len(highs) == len(closes) and len(lows) == len(closes)
    adx_line = plus_di = minus_di = None
    trend_direction = None
    if has_ohlc:
        adx_line, plus_di, minus_di = adx(highs, lows, closes, period=_ADX_PERIOD)
        _, trend_direction = supertrend(highs, lows, closes, _SUPERTREND_PERIOD, _SUPERTREND_MULTIPLIER)

    macd_line_prev = macd_line.iloc[-2] if len(macd_line) >= 2 else None
    macd_signal_prev = macd_signal.iloc[-2] if len(macd_signal) >= 2 else None

    return IndicatorSnapshot(
        close=float(closes.iloc[-1]),
        rsi14=_safe_float(rsi_series.iloc[-1]),
        ema200=_safe_float(ema_series.iloc[-1]),
        macd_line=_safe_float(macd_line.iloc[-1]),
        macd_signal=_safe_float(macd_signal.iloc[-1]),
        macd_line_prev=_safe_float(macd_line_prev),
        macd_signal_prev=_safe_float(macd_signal_prev),
        volume=_safe_float(volumes.iloc[-1]) if len(volumes) else None,
        volume_sma20=_safe_float(volume_sma.iloc[-1]) if len(volume_sma) else None,
        bb_lower=_safe_float(bb_lower.iloc[-1]),
        bb_upper=_safe_float(bb_upper.iloc[-1]),
        adx14=_safe_float(adx_line.iloc[-1]) if adx_line is not None else None,
        plus_di14=_safe_float(plus_di.iloc[-1]) if plus_di is not None else None,
        minus_di14=_safe_float(minus_di.iloc[-1]) if minus_di is not None else None,
        supertrend_direction=_direction_or_none(trend_direction, 1) if trend_direction is not None else None,
        supertrend_direction_prev=_direction_or_none(trend_direction, 2) if trend_direction is not None else None,
    )


# ------------------------------------------------------------------
# Filtreler — her biri IndicatorSnapshot üzerinde saf bool predicate.
# ------------------------------------------------------------------

def is_rsi_oversold(snap: IndicatorSnapshot) -> bool:
    """RSI < 35 (Aşırı satım / dip bölgesi)."""
    if snap.rsi14 is None:
        return False
    return snap.rsi14 < 35.0


def is_rsi_overbought(snap: IndicatorSnapshot) -> bool:
    """RSI > 65 (Aşırı alım / güçlü ivme veya zirve)."""
    if snap.rsi14 is None:
        return False
    return snap.rsi14 > 65.0


def is_rsi_oversold_above_ema200(snap: IndicatorSnapshot) -> bool:
    """RSI < 35 + Fiyat > EMA200 (Yükselen trend içi düzeltme alımı)."""
    if snap.rsi14 is None or snap.ema200 is None:
        return False
    return snap.rsi14 < 35.0 and snap.close > snap.ema200


def is_macd_bullish_cross(snap: IndicatorSnapshot) -> bool:
    """MACD çizgisi sinyal çizgisini yukarı kesmiş."""
    required = (snap.macd_line, snap.macd_signal, snap.macd_line_prev, snap.macd_signal_prev)
    if any(v is None for v in required):
        return False
    return snap.macd_line_prev <= snap.macd_signal_prev and snap.macd_line > snap.macd_signal


def is_macd_bullish_cross_with_volume_spike(snap: IndicatorSnapshot) -> bool:
    """MACD bullish kesişim + Hacim > 20 günlük ortalama."""
    if not is_macd_bullish_cross(snap):
        return False
    if snap.volume is None or snap.volume_sma20 is None:
        return False
    return snap.volume > snap.volume_sma20


def is_volume_spike(snap: IndicatorSnapshot) -> bool:
    """Hacim > 20 günlük ortalamanın 1.5 katı."""
    if snap.volume is None or snap.volume_sma20 is None:
        return False
    return snap.volume > snap.volume_sma20 * 1.5


def is_touching_lower_bollinger_band(snap: IndicatorSnapshot) -> bool:
    """Fiyat Bollinger alt bandına değmiş veya %2 yakınına inmiş."""
    if snap.bb_lower is None:
        return False
    return snap.close <= snap.bb_lower * 1.02


def is_touching_upper_bollinger_band(snap: IndicatorSnapshot) -> bool:
    """Fiyat Bollinger üst bandına değmiş veya üstüne çıkmış."""
    if snap.bb_upper is None:
        return False
    return snap.close >= snap.bb_upper * 0.98


def is_adx_strong_uptrend(snap: IndicatorSnapshot) -> bool:
    """ADX > 25 (güçlü trend) ve +DI > -DI (yön yukarı)."""
    if snap.adx14 is None or snap.plus_di14 is None or snap.minus_di14 is None:
        return False
    return snap.adx14 > _ADX_STRONG_TREND and snap.plus_di14 > snap.minus_di14


def is_supertrend_buy_signal(snap: IndicatorSnapshot) -> bool:
    """Supertrend son barda düşüşten (-1) yükselişe (+1) döndü."""
    return snap.supertrend_direction_prev == -1 and snap.supertrend_direction == 1


class ScreenerFilterDef(NamedTuple):
    label: str
    predicate: Callable[[IndicatorSnapshot], bool]


SCREENER_FILTERS: dict[str, ScreenerFilterDef] = {
    "bollinger_lower_band_touch": ScreenerFilterDef(
        label="Bollinger Alt Bandına Değme (Dip)",
        predicate=is_touching_lower_bollinger_band,
    ),
    "macd_bullish_cross": ScreenerFilterDef(
        label="MACD Al Kesişimi",
        predicate=is_macd_bullish_cross,
    ),
    "macd_bullish_cross_volume_spike": ScreenerFilterDef(
        label="MACD Kesişim + Hacim Patlaması",
        predicate=is_macd_bullish_cross_with_volume_spike,
    ),
    "rsi_oversold": ScreenerFilterDef(
        label="Aşırı Satım (RSI < 35 Dip Avcısı)",
        predicate=is_rsi_oversold,
    ),
    "rsi_oversold_above_ema200": ScreenerFilterDef(
        label="Aşırı Satım (RSI<35) + EMA200 Üzeri",
        predicate=is_rsi_oversold_above_ema200,
    ),
    "volume_spike": ScreenerFilterDef(
        label="Güçlü Hacim Artışı (>1.5x)",
        predicate=is_volume_spike,
    ),
    "bollinger_upper_band_touch": ScreenerFilterDef(
        label="Bollinger Üst Bandını Zorlayanlar (Trend Gücü)",
        predicate=is_touching_upper_bollinger_band,
    ),
    "rsi_overbought": ScreenerFilterDef(
        label="Aşırı Alım (RSI > 65)",
        predicate=is_rsi_overbought,
    ),
    "adx_strong_uptrend": ScreenerFilterDef(
        label="Güçlü Yükseliş Trendi (ADX > 25, +DI > -DI)",
        predicate=is_adx_strong_uptrend,
    ),
    "supertrend_buy_signal": ScreenerFilterDef(
        label="Supertrend Al Sinyali (Trend Dönüşü)",
        predicate=is_supertrend_buy_signal,
    ),
}

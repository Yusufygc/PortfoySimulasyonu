"""
BIST Çoklu Sinyal Tarayıcısı — saf indikatör anlık görüntüsü (snapshot) ve filtreler.

Ağsız, durumsuz, IO yok — saf fonksiyonlar (golden_cross.py ile aynı desen).
DB erişimi ve orkestrasyon `screener_service.py`'dedir.

Hazır filtreler (bkz. TRANSFORMATION_PLAN.md §3.1):
- rsi_oversold_above_ema200: RSI < 30 (aşırı satım) + Fiyat > EMA200
- macd_bullish_cross_volume_spike: MACD bullish kesişim + Hacim > 20 günlük ortalama
- bollinger_lower_band_touch: Fiyat, Bollinger alt bandına değmiş/altına inmiş
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, NamedTuple, Optional

import pandas as pd

from src.application.services.analysis.technical.indicators import (
    bollinger_bands,
    ema,
    macd,
    rsi,
    sma,
)

_RSI_PERIOD = 14
_EMA_TREND_PERIOD = 200
_MACD_FAST, _MACD_SLOW, _MACD_SIGNAL = 12, 26, 9
_BOLLINGER_PERIOD, _BOLLINGER_STD = 20, 2.0
_VOLUME_SMA_PERIOD = 20
_RSI_OVERSOLD_THRESHOLD = 30.0


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


def _safe_float(value) -> Optional[float]:
    if value is None or pd.isna(value):
        return None
    return float(value)


def build_snapshot(
    closes: pd.Series,
    highs: pd.Series,
    lows: pd.Series,
    volumes: pd.Series,
) -> Optional[IndicatorSnapshot]:
    """Son bar için indikatör anlık görüntüsü üretir.

    closes: Index=tarih (sıralı asc), value=kapanış. highs/lows/volumes opsiyoneldir
    (OHLCV verisi olmayan hisseler için tamamen NaN geçilebilir — o zaman hacim/OHLC-bağımlı
    alanlar None döner, close-only alanlar (rsi/ema/macd/bollinger) yine hesaplanır).

    Yetersiz veri (close serisi boş veya son bar NaN) → None.
    """
    if len(closes) == 0 or pd.isna(closes.iloc[-1]):
        return None

    rsi_series = rsi(closes, period=_RSI_PERIOD)
    ema_series = ema(closes, period=_EMA_TREND_PERIOD)
    macd_line, macd_signal, _ = macd(closes, _MACD_FAST, _MACD_SLOW, _MACD_SIGNAL)
    _, _, bb_lower = bollinger_bands(closes, period=_BOLLINGER_PERIOD, num_std=_BOLLINGER_STD)
    volume_sma = sma(volumes, period=_VOLUME_SMA_PERIOD) if len(volumes) else pd.Series(dtype=float)

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
    )


# ------------------------------------------------------------------
# Filtreler — her biri IndicatorSnapshot üzerinde saf bool predicate.
# Gerekli alanlardan biri None ise (yetersiz veri) filtre eşleşmez (False).
# ------------------------------------------------------------------

def is_rsi_oversold_above_ema200(snap: IndicatorSnapshot) -> bool:
    if snap.rsi14 is None or snap.ema200 is None:
        return False
    return snap.rsi14 < _RSI_OVERSOLD_THRESHOLD and snap.close > snap.ema200


def is_macd_bullish_cross_with_volume_spike(snap: IndicatorSnapshot) -> bool:
    required = (
        snap.macd_line, snap.macd_signal,
        snap.macd_line_prev, snap.macd_signal_prev,
        snap.volume, snap.volume_sma20,
    )
    if any(v is None for v in required):
        return False
    crossed_up = snap.macd_line_prev <= snap.macd_signal_prev and snap.macd_line > snap.macd_signal
    volume_spike = snap.volume > snap.volume_sma20
    return crossed_up and volume_spike


def is_touching_lower_bollinger_band(snap: IndicatorSnapshot) -> bool:
    if snap.bb_lower is None:
        return False
    return snap.close <= snap.bb_lower


class ScreenerFilterDef(NamedTuple):
    label: str
    predicate: Callable[[IndicatorSnapshot], bool]


SCREENER_FILTERS: dict[str, ScreenerFilterDef] = {
    "rsi_oversold_above_ema200": ScreenerFilterDef(
        label="Aşırı Satım (RSI<30) + EMA200 Üzeri",
        predicate=is_rsi_oversold_above_ema200,
    ),
    "macd_bullish_cross_volume_spike": ScreenerFilterDef(
        label="MACD Bullish Kesişim + Hacim Patlaması",
        predicate=is_macd_bullish_cross_with_volume_spike,
    ),
    "bollinger_lower_band_touch": ScreenerFilterDef(
        label="Bollinger Alt Bandına Değme",
        predicate=is_touching_lower_bollinger_band,
    ),
}

"""
Golden / Death Cross saf vektörel hesap.

Tek bir kapanış serisinden EMA(short) ile EMA(long) kesişimlerini çıkarır.
Ağsız, durumsuz, IO yok — saf fonksiyon.

Standart:
- EMA(50) > EMA(200) yukarı keser → Golden Cross (boğa sinyali)
- EMA(50) < EMA(200) aşağı keser → Death Cross (ayı sinyali)

TradingView uyumluluğu: EMA seed'i ilk `span` barın SMA'sından başlar.
Pandas varsayılanı (adjust=False) ilk fiyatı seed alır — bu tarih kaymasına neden olur.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd

from src.domain.models.golden_cross_event import CrossType

# EMA200 güvenilir converge için gereken minimum bar sayısı.
# TradingView da bu miktarın altında EMA200 göstermez.
_MIN_BARS_MULTIPLIER = 2


@dataclass(frozen=True)
class DetectedCross:
    """detect_crosses() dönüş değeri — pure veri (DB yok)."""
    cross_date: date
    cross_type: CrossType
    short_ma: Decimal
    long_ma: Decimal
    close_price: Decimal


def _ema_tv(series: pd.Series, span: int) -> pd.Series:
    """TradingView uyumlu EMA: ilk `span` barın SMA'sı seed, sonra α*(price)+(1-α)*prev.

    numpy array üzerinde döngü → pandas .iloc'tan ~10x hızlı.
    """
    alpha = 2.0 / (span + 1)
    values = series.to_numpy(dtype=float)
    n = len(values)
    out = np.full(n, float("nan"))

    if n < span:
        return pd.Series(out, index=series.index)

    out[span - 1] = values[:span].mean()
    for i in range(span, n):
        out[i] = alpha * values[i] + (1.0 - alpha) * out[i - 1]

    return pd.Series(out, index=series.index)


def detect_crosses(
    closes: pd.Series,
    short: int = 50,
    long: int = 200,
) -> list[DetectedCross]:
    """
    closes: pd.Series — Index=date (sorted asc), value=numeric close.
    Dönüş: kronolojik sırada (en eski önce) tüm cross olayları.

    Yetersiz veri (< long * 2 satır) → boş liste.
    EMA değerleri NaN olan barlar (warmup dönemi) → atlanır.
    """
    min_bars = long * _MIN_BARS_MULTIPLIER
    if closes is None or len(closes) < min_bars:
        return []

    ema_s = _ema_tv(closes, short)
    ema_l = _ema_tv(closes, long)
    diff  = ema_s - ema_l
    sign  = diff.gt(0)              # True iff ema_s > ema_l
    prev  = sign.shift(1)

    # Cross noktaları: sign != prev, her iki EMA da NaN değil (warmup dışı)
    cross_mask = sign.ne(prev) & prev.notna() & ema_l.notna() & ema_s.notna()

    events: list[DetectedCross] = []
    for idx in closes.index[cross_mask]:
        is_golden = bool(sign.loc[idx])
        events.append(DetectedCross(
            cross_date=_as_date(idx),
            cross_type=CrossType.GOLDEN if is_golden else CrossType.DEATH,
            short_ma=Decimal(str(round(ema_s.loc[idx], 4))),
            long_ma=Decimal(str(round(ema_l.loc[idx], 4))),
            close_price=Decimal(str(closes.loc[idx])),
        ))
    return events


def _as_date(value) -> date:
    if isinstance(value, date) and not hasattr(value, "hour"):
        return value
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime().date()
    if hasattr(value, "date"):
        return value.date()
    return value

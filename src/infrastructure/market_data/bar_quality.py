"""BIST günlük barlarında hayalet (gerçek işlem görmemiş) bar tespiti.

Yahoo, BIST'in kapalı olduğu günler (bayram, resmî tatil) ve bazı veri boşlukları için hacmi 0, açılış = yüksek =
düşük = kapanış (önceki kapanış) olan barlar döndürür. Bu barlar işlem günü sayılırsa hareketli ortalama pencereleri
kayar, sıfır getirili günler oynaklığı düşürür ve grafikte sahte mumlar görünür.

Kural (yalnızca BIST hisseleri için):
- hacim 0 ve açılış = yüksek = düşük = kapanış -> hayalet;
- tatil takviminin kapsadığı yıllarda (2020+) BIST'in kapalı olduğu gün -> hayalet. Takvim öncesi yıllarda yalnızca
  ilk kural uygulanır (ör. 15 Temmuz 2017'den önce işlem günüydü).
Arife (yarım gün) barı gerçek hacimliyse korunur.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Optional, Tuple

from src.infrastructure.calendar.bist_holiday_calendar import is_bist_trading_day

CALENDAR_FROM = date(2020, 1, 1)


def _num(value) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(number) else number


OHLCV = Tuple[object, object, object, object, object]  # (açılış, yüksek, düşük, kapanış, hacim)


def is_flat_zero_volume(ohlcv: OHLCV) -> bool:
    *raw_prices, volume = ohlcv
    prices = [_num(p) for p in raw_prices]
    if any(p is None for p in prices) or (_num(volume) or 0) != 0:
        return False
    return max(prices) == min(prices)


def is_ghost_bar(price_date: date, ohlcv: OHLCV) -> bool:
    if price_date >= CALENDAR_FROM and not is_bist_trading_day(price_date):
        return True
    return is_flat_zero_volume(ohlcv)

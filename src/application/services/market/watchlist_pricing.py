"""İzleme listesi satır fiyatı: günlük barlar ve (varsa) güncel canlı fiyattan fiyat, günlük fark, aralık ve trend.

Saf fonksiyonlardır. Günlük barlar yalnızca gün sonunda yazıldığı için seans içinde fiyat bu barlardan "donmuş" görünür;
canlı fiyat önbelleği (`latest_prices`) kayıt seans içinde alınmışsa barların üzerine bindirilir (karar çağıranda).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, List, Optional, Sequence

_SPARKLINE_POINTS = 10


@dataclass(frozen=True)
class RowPricing:
    price: float
    daily_diff_pct: float
    day_low: float
    day_high: float
    day_range_pct: float
    volume_text: str
    sparkline: List[float]


# Fiyatı bulunamayan hisse için sabit görünüm
DEFAULT_PRICING = RowPricing(100.0, 0.0, 98.0, 102.0, 0.5, "-", [100.0, 100.0])


def _volume_text(bar: Any) -> str:
    volume = getattr(bar, "volume", None)
    return f"{float(volume) / 1e6:.1f}M" if volume else "-"


def _range_pct(price: float, low: float, high: float) -> float:
    return max(0.0, min(1.0, (price - low) / max(0.01, high - low)))


def _diff_pct(price: float, previous_close: float) -> float:
    return (price - previous_close) / previous_close * 100 if previous_close > 0 else 0.0


def _bar_low_high(bar: Any, price: float) -> tuple:
    low = float(bar.low_price) if getattr(bar, "low_price", None) else price * 0.985
    high = float(bar.high_price) if getattr(bar, "high_price", None) else price * 1.015
    return low, high


def price_from_bars(bars: Sequence[Any]) -> Optional[RowPricing]:
    """Yalnızca günlük barlardan fiyatlama; bar yoksa None."""
    if not bars:
        return None
    last = bars[-1]
    price = float(last.close_price)
    previous_close = float(bars[-2].close_price) if len(bars) > 1 else price
    low, high = _bar_low_high(last, price)
    return RowPricing(
        price=price,
        daily_diff_pct=_diff_pct(price, previous_close),
        day_low=low,
        day_high=high,
        day_range_pct=_range_pct(price, low, high),
        volume_text=_volume_text(last),
        sparkline=[float(b.close_price) for b in bars[-_SPARKLINE_POINTS:]],
    )


def price_with_live(bars: Sequence[Any], live_price: float, live_date: date) -> RowPricing:
    """Canlı fiyatı günlük barların üzerine bindirir.

    Son bar canlı fiyatla aynı gündeyse o gün bar güncellenir (önceki kapanış bir önceki bardır); son bar daha eskiyse
    canlı fiyat yeni günün ilk noktası sayılır (önceki kapanış son bardır).
    """
    if not bars:
        return RowPricing(live_price, 0.0, live_price, live_price, 0.5, "-", [live_price, live_price])
    last = bars[-1]
    last_close = float(last.close_price)
    low, high = _bar_low_high(last, last_close)
    low, high = min(low, live_price), max(high, live_price)
    if last.price_date >= live_date:
        previous_close = float(bars[-2].close_price) if len(bars) > 1 else last_close
        history = [float(b.close_price) for b in bars[:-1]]
    else:
        previous_close = last_close
        history = [float(b.close_price) for b in bars]
    return RowPricing(
        price=live_price,
        daily_diff_pct=_diff_pct(live_price, previous_close),
        day_low=low,
        day_high=high,
        day_range_pct=_range_pct(live_price, low, high),
        volume_text=_volume_text(last),
        sparkline=(history + [live_price])[-_SPARKLINE_POINTS:],
    )


def price_row(bars: Sequence[Any], live_price: Optional[float], live_date: Optional[date]) -> Optional[RowPricing]:
    """Uygulanacak canlı fiyat varsa barların üzerine bindirir, yoksa yalnızca barlardan fiyatlar.

    Canlı fiyatın uygulanıp uygulanmayacağına çağıran karar verir (`CurrentPriceResolver.live_applies`, Ana Sayfa ile
    aynı kural); seans dışında alınmış kayıt bindirilseydi günlük fark yanlışlıkla %0 görünürdü.
    """
    if live_price is None or live_date is None:
        return price_from_bars(bars)
    return price_with_live(bars, float(live_price), live_date)

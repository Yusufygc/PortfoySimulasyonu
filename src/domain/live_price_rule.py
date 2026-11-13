"""Canlı (gün içi) fiyatın son günlük kapanışın yerine geçip geçmeyeceği kuralı.

İki fiyat kaynağı vardır: `latest_prices` (canlı yenileme yazar) ve günlük barlar (kapanış senkronu yazar).
Canlı kayıt yalnızca bir işlem gününün seans penceresinde (açılış ile kapanış verisinin hazır olduğu an arası)
alınmışsa gün içi fiyattır. Seans dışında veri kaynağı son kapanışı "güncel fiyat" olarak verir; bu kayıt yeni bir
günün fiyatı sayılırsa önceki kapanış aynı fiyat olur ve günlük değişim yanlışlıkla %0 görünür.

Pencere bilgisi (işlem günü, yarım gün, kapanış gecikmesi) uygulama katmanındaki seans servisinden gelir.
Tüm zamanlar Istanbul duvar saatidir (naive).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Callable, Optional, Tuple

INTRADAY_SOURCE = "intraday"

# İşlem günü için (seans açılışı, kapanış verisinin hazır olduğu an); işlem günü değilse None
SessionWindow = Callable[[date], Optional[Tuple[datetime, datetime]]]


def live_price_applies(
    source: str,
    as_of: datetime,
    last_bar_date: Optional[date],
    now: datetime,
    session_window: SessionWindow,
) -> bool:
    """Canlı kayıt son günlük kapanış yerine kullanılmalı mı?

    - Kayıt seans penceresinde alınmamışsa (gece, hafta sonu, tatil, seans öncesi) kullanılmaz.
    - Son bardan daha yeni bir güne aitse kullanılır (o günün kapanışı henüz yazılmamış).
    - Son barla aynı güne aitse yalnızca o günün kapanış verisi henüz hazır değilken kullanılır; hazır olduktan sonra
      o günün barı kesin kapanıştır.
    """
    if source != INTRADAY_SOURCE:
        return False
    day = as_of.date()
    window = session_window(day)
    if window is None:
        return False
    opens_at, close_ready_at = window
    if not opens_at <= as_of < close_ready_at:
        return False
    if last_bar_date is None or day > last_bar_date:
        return True
    return day == last_bar_date and now < close_ready_at

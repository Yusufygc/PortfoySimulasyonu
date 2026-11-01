from __future__ import annotations

import logging
from datetime import datetime, time, timezone, tzinfo
from typing import Optional

from src.domain.models.asset import AssetClass

logger = logging.getLogger(__name__)

_US_OPEN = time(9, 30)
_US_CLOSE = time(16, 0)
_METAL_REOPEN = time(18, 0)     # CME Globex: pazar 18:00 ET açılış, her gün 17:00-18:00 ET mola
_METAL_BREAK_START = time(17, 0)


def _load_new_york() -> Optional[tzinfo]:
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("America/New_York")
    except Exception:  # tzdata yok (ör. derlenmiş paket): ABD saatleri hesaplanamaz
        logger.warning("America/New_York saat dilimi bulunamadı; ABD hisse ve emtia seansı hep açık sayılacak.")
        return None


class AssetMarketCalendar:
    """Varlık sınıfına göre piyasanın açık olup olmadığı.

    Kripto 7/24; ABD hisseleri New York 09:30-16:00 hafta içi; kıymetli maden vadeli kontratları CME Globex
    (pazar 18:00 ET - cuma 17:00 ET, günlük 17:00-18:00 ET mola). Resmî tatiller modellenmez (tatil günü
    "açık" görünür, yenileme yalnızca boşa bir istek yapar). Saat dilimi verisi yoksa seans hep açık sayılır.
    """

    def __init__(self) -> None:
        self._new_york = _load_new_york()

    def is_open(self, asset_class: AssetClass, utc_now: datetime) -> bool:
        if asset_class == AssetClass.CRYPTO or self._new_york is None:
            return True
        moment = utc_now if utc_now.tzinfo is not None else utc_now.replace(tzinfo=timezone.utc)
        local = moment.astimezone(self._new_york)
        if asset_class == AssetClass.US_STOCK:
            return local.weekday() < 5 and _US_OPEN <= local.time() < _US_CLOSE
        if asset_class == AssetClass.PRECIOUS_METAL:
            return self._metal_futures_open(local)
        return True

    @staticmethod
    def _metal_futures_open(local: datetime) -> bool:
        weekday, clock = local.weekday(), local.time()
        if weekday == 5:  # cumartesi
            return False
        if weekday == 6:  # pazar yalnızca 18:00'den sonra
            return clock >= _METAL_REOPEN
        if weekday == 4 and clock >= _METAL_BREAK_START:  # cuma 17:00'den sonra kapalı
            return False
        return not (_METAL_BREAK_START <= clock < _METAL_REOPEN)

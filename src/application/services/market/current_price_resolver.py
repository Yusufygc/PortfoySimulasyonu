"""
CurrentPriceResolver — Portföy değerlemesi için "güncel fiyat" kaynağını doğru seçer.

İki kaynak vardır:
- `latest_prices`: canlı/gün içi fiyat önbelleği (yalnızca canlı yenileme çalışınca güncellenir)
- `daily_prices`: günlük kapanışlar (piyasa senkronu ve veri tamamlama ile güncellenir)

Canlı yenileme çalışmadığında `latest_prices` günlerce eski kalabilir. Eski bir canlı fiyatı yeni
kapanışlarla karşılaştırmak anlamsız günlük değişim üretir. Bu sınıf, canlı fiyat yalnızca son
günlük kapanıştan **daha yeni bir güne** aitse onu kullanır; aksi halde son kapanışı döndürür.
Günlük değişim için önceki kapanış, seçilen fiyatın gününden **önceki** son kapanıştır.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Optional, Sequence

logger = logging.getLogger(__name__)

SOURCE_LIVE = "live"
SOURCE_DAILY = "daily"


@dataclass(frozen=True)
class ResolvedPrice:
    price: Decimal
    price_date: date
    source: str  # "live" | "daily"


class CurrentPriceResolver:
    def __init__(self, latest_price_repo, price_repo) -> None:
        self._latest_price_repo = latest_price_repo
        self._price_repo = price_repo

    def resolve(self, stock_ids: Sequence[int]) -> Dict[int, ResolvedPrice]:
        ids = [sid for sid in dict.fromkeys(stock_ids) if sid is not None]
        if not ids:
            return {}
        live = self._read_live(ids)
        last_dates = self._read_last_daily_dates(ids)

        result: Dict[int, ResolvedPrice] = {}
        for sid in ids:
            live_price = live.get(sid)
            daily_date = last_dates.get(sid)
            live_date = live_price.as_of.date() if live_price is not None else None

            if live_price is not None and (daily_date is None or live_date > daily_date):
                result[sid] = ResolvedPrice(live_price.price, live_date, SOURCE_LIVE)
                continue
            daily = self._read_daily_close(sid, daily_date) if daily_date is not None else None
            if daily is not None:
                result[sid] = ResolvedPrice(daily, daily_date, SOURCE_DAILY)
            elif live_price is not None:
                # Günlük kapanış okunamadıysa eski de olsa canlı fiyat hiç yoktan iyidir
                result[sid] = ResolvedPrice(live_price.price, live_date, SOURCE_LIVE)
        return result

    def price_map(self, stock_ids: Sequence[int]) -> Dict[int, Decimal]:
        return {sid: resolved.price for sid, resolved in self.resolve(stock_ids).items()}

    def previous_close(self, stock_id: int, resolved: ResolvedPrice) -> Optional[Decimal]:
        """Seçilen fiyatın gününden önceki son geçerli kapanış.

        `get_last_price_before` "verilen gün dahil" semantiğine sahiptir; seçilen günün kendi kapanışını
        önceki kapanış sanmamak için bir gün öncesi istenir.
        """
        try:
            previous = self._price_repo.get_last_price_before(stock_id, resolved.price_date - timedelta(days=1))
        except Exception as exc:
            logger.debug("Önceki kapanış okunamadı (stock_id=%s): %s", stock_id, exc)
            return None
        if previous is not None and previous.close_price and previous.close_price > 0:
            return Decimal(str(previous.close_price))
        return None

    def daily_change_pct(self, stock_id: int, resolved: ResolvedPrice) -> Optional[Decimal]:
        previous = self.previous_close(stock_id, resolved)
        if previous is None:
            return None
        return (resolved.price - previous) / previous * Decimal("100")

    # ------------------------------------------------------------------ okuma yardımcıları

    def _read_live(self, ids: Sequence[int]) -> dict:
        if self._latest_price_repo is None:
            return {}
        try:
            return self._latest_price_repo.get_latest_prices(ids) or {}
        except Exception as exc:
            logger.debug("Canlı fiyatlar okunamadı: %s", exc)
            return {}

    def _read_last_daily_dates(self, ids: Sequence[int]) -> Dict[int, date]:
        if self._price_repo is None:
            return {}
        try:
            return self._price_repo.get_latest_price_dates(ids) or {}
        except Exception as exc:
            logger.debug("Son kapanış tarihleri okunamadı: %s", exc)
            return {}

    def _read_daily_close(self, stock_id: int, price_date: date) -> Optional[Decimal]:
        try:
            row = self._price_repo.get_price_for_date(stock_id, price_date)
        except Exception as exc:
            logger.debug("Günlük kapanış okunamadı (stock_id=%s): %s", stock_id, exc)
            return None
        if row is not None and row.close_price and row.close_price > 0:
            return Decimal(str(row.close_price))
        return None

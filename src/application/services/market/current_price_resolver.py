"""
CurrentPriceResolver — Portföy değerlemesi için "güncel fiyat" kaynağını doğru seçer.

İki kaynak vardır:
- `latest_prices`: canlı/gün içi fiyat önbelleği (yalnızca canlı yenileme çalışınca güncellenir)
- `daily_prices`: günlük kapanışlar (piyasa senkronu ve veri tamamlama ile güncellenir)

Canlı yenileme çalışmadığında `latest_prices` günlerce eski kalabilir; seans dışında çekilen kayıt da yeni bir günün
fiyatı değildir. Eski bir canlı fiyatı yeni kapanışlarla karşılaştırmak anlamsız günlük değişim üretir. Canlı kaydın
kullanılıp kullanılmayacağı `src/domain/live_price_rule.live_price_applies` kuralıyla (seans penceresi, Istanbul saati)
belirlenir; aksi halde son kapanış döner. Günlük değişim için önceki kapanış, seçilen fiyatın gününden **önceki** son
kapanıştır. İzleme listesi de aynı kuralı `live_applies` üzerinden kullanır.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional, Sequence

from src.application.services.market.bist_market_session_service import BistMarketSessionService
from src.domain.live_price_rule import live_price_applies
from src.domain.market_clock import market_now, to_market_date, to_market_datetime

logger = logging.getLogger(__name__)

SOURCE_LIVE = "live"
SOURCE_DAILY = "daily"


@dataclass(frozen=True)
class ResolvedPrice:
    price: Decimal
    price_date: date
    source: str  # "live" | "daily"


class CurrentPriceResolver:
    def __init__(self, latest_price_repo, price_repo, session_service: BistMarketSessionService | None = None) -> None:
        self._latest_price_repo = latest_price_repo
        self._price_repo = price_repo
        self._session = session_service or BistMarketSessionService()

    def live_applies(self, live: Any, last_bar_date: Optional[date], now: Optional[datetime] = None) -> bool:
        """Canlı kayıt (LatestPrice) son günlük kapanışın yerine geçmeli mi? (bkz. `live_price_applies`)"""
        if live is None or getattr(live, "as_of", None) is None:
            return False
        return live_price_applies(
            getattr(live, "source", ""),
            to_market_datetime(live.as_of),
            last_bar_date,
            now or market_now(),
            self._session.session_window,
        )

    def resolve(self, stock_ids: Sequence[int]) -> Dict[int, ResolvedPrice]:
        ids = [sid for sid in dict.fromkeys(stock_ids) if sid is not None]
        if not ids:
            return {}
        live = self._read_live(ids)
        last_dates = self._read_last_daily_dates(ids)
        now = market_now()

        result: Dict[int, ResolvedPrice] = {}
        for sid in ids:
            live_price = live.get(sid)
            daily_date = last_dates.get(sid)
            live_date = to_market_date(live_price.as_of) if live_price is not None and live_price.as_of else None

            if live_price is not None and self.live_applies(live_price, daily_date, now):
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

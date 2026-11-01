from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Callable, List, Optional

from src.application.services.assets.asset_market_calendar import AssetMarketCalendar
from src.domain.market_clock import market_today
from src.domain.models.asset import Asset
from src.domain.models.asset_price import AssetLatestPrice, AssetPrice
from src.domain.ports.repositories.i_asset_price_repo import IAssetPriceRepository
from src.domain.ports.repositories.i_asset_repo import IAssetRepository
from src.domain.ports.services.i_asset_price_provider import IAssetPriceProvider

logger = logging.getLogger(__name__)

SOURCE = "yfinance"
DEFAULT_BACKFILL_DAYS = 365


def _utc_now() -> datetime:
    """Saat dilimsiz UTC; testlerde `now_provider` ile değiştirilir."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True)
class AssetRefreshResult:
    """Son fiyat yenilemesinin özeti: güncellenen, seans kapalı olduğu için atlanan ve fiyatı alınamayan semboller."""

    updated: List[str] = field(default_factory=list)
    skipped_closed: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)


class AssetPriceRefreshService:
    """Varlık defterindeki aktif varlıkların fiyatını sağlayıcıdan çekip kaydeder (BIST kurallarından bağımsız)."""

    def __init__(
        self,
        asset_repo: IAssetRepository,
        price_repo: IAssetPriceRepository,
        provider: IAssetPriceProvider,
        calendar: Optional[AssetMarketCalendar] = None,
        now_provider: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._asset_repo = asset_repo
        self._price_repo = price_repo
        self._provider = provider
        self._calendar = calendar or AssetMarketCalendar()
        self._now = now_provider

    def refresh_latest(self, only_open: bool = True) -> AssetRefreshResult:
        """Aktif varlıkların son fiyatını yeniler; `only_open` iken seansı kapalı sınıflar atlanır."""
        assets = self._asset_repo.list_assets(active_only=True)
        now = self._now()
        due: List[Asset] = []
        skipped: List[str] = []
        for asset in assets:
            if only_open and not self._calendar.is_open(asset.asset_class, now):
                skipped.append(asset.symbol)
            else:
                due.append(asset)
        if not due:
            return AssetRefreshResult(skipped_closed=skipped)

        quotes = self._provider.get_latest([asset.yf_symbol for asset in due])
        records: List[AssetLatestPrice] = []
        updated: List[str] = []
        missing: List[str] = []
        for asset in due:
            quote = quotes.get(asset.yf_symbol)
            if quote is None:
                missing.append(asset.symbol)
                continue
            records.append(AssetLatestPrice(
                id=None, asset_id=asset.id, price=quote.price, currency_code=asset.quote_currency,
                as_of=quote.as_of, source=SOURCE, fetched_at=now,
            ))
            updated.append(asset.symbol)
        self._price_repo.upsert_latest_prices(records)
        return AssetRefreshResult(updated=updated, skipped_closed=skipped, missing=missing)

    def backfill_history(self, asset_id: int, start: Optional[date] = None, end: Optional[date] = None) -> int:
        """Varlığın günlük kapanış geçmişini çekip kaydeder (yeni varlık eklenince); kaydedilen gün sayısını döner."""
        asset = self._asset_repo.get_asset(asset_id)
        if asset is None:
            raise ValueError("Varlık bulunamadı.")
        end_date = end or market_today()
        start_date = start or end_date - timedelta(days=DEFAULT_BACKFILL_DAYS)
        points = self._provider.get_history(asset.yf_symbol, start_date, end_date)
        self._price_repo.upsert_daily_prices(
            AssetPrice(None, asset.id, point_date, close, asset.quote_currency, SOURCE) for point_date, close in points
        )
        return len(points)

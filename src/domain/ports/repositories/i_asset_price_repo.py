from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Sequence

from src.domain.models.asset_price import AssetLatestPrice, AssetPrice


class IAssetPriceRepository(ABC):
    """Varlık günlük kapanış ve son fiyat deposu."""

    @abstractmethod
    def upsert_daily_prices(self, prices: Iterable[AssetPrice]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_daily_prices(
        self, asset_id: int, start: Optional[date] = None, end: Optional[date] = None
    ) -> List[AssetPrice]:
        """Tarihe göre artan sıralı kapanış fiyatları."""
        raise NotImplementedError

    @abstractmethod
    def get_last_daily_price(self, asset_id: int, on_or_before: Optional[date] = None) -> Optional[AssetPrice]:
        raise NotImplementedError

    @abstractmethod
    def upsert_latest_prices(self, prices: Iterable[AssetLatestPrice]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_latest_prices(self, asset_ids: Sequence[int]) -> Dict[int, AssetLatestPrice]:
        raise NotImplementedError

    @abstractmethod
    def get_latest_price_map(self, asset_ids: Sequence[int]) -> Dict[int, Decimal]:
        raise NotImplementedError

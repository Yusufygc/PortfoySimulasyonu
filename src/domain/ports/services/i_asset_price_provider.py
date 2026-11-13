from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import Dict, List, Sequence, Tuple

from src.domain.models.asset_price import AssetQuote


class IAssetPriceProvider(ABC):
    """BIST dışı varlık ve kur sembolleri için fiyat sağlayıcı (sembol sağlayıcıya olduğu gibi verilir)."""

    @abstractmethod
    def get_latest(self, symbols: Sequence[str]) -> Dict[str, AssetQuote]:
        """Her sembolün son fiyatı; alınamayan semboller sonuçta yer almaz (istisna fırlatmaz)."""
        raise NotImplementedError

    @abstractmethod
    def get_history(self, symbol: str, start: date, end: date) -> List[Tuple[date, Decimal]]:
        """Tarihe göre artan günlük kapanışlar. Sağlayıcıya ulaşılamazsa `MarketDataUnavailableError`."""
        raise NotImplementedError

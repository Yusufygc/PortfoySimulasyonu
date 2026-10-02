from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from src.domain.models.market_indicator import IndicatorQuote


class IMarketIndicatorProvider(ABC):
    """Kur, emtia ve endeks göstergeleri için anlık fiyat sağlayıcı (canlı, hafif sorgu)."""

    @abstractmethod
    def get_quote(self, symbol: str) -> Optional[IndicatorQuote]:
        """Sembolün son fiyatı ve önceki kapanışı; alınamazsa None (istisna fırlatmaz)."""
        raise NotImplementedError

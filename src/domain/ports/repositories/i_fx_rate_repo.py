from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Iterable, List, Optional

from src.domain.models.asset_price import FxRate


class IFxRateRepository(ABC):
    """Günlük kur serisi deposu."""

    @abstractmethod
    def upsert_rates(self, rates: Iterable[FxRate]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_rates(
        self, base_currency: str, quote_currency: str, start: Optional[date] = None, end: Optional[date] = None
    ) -> List[FxRate]:
        """Tarihe göre artan sıralı kurlar."""
        raise NotImplementedError

    @abstractmethod
    def get_rate_on_or_before(self, base_currency: str, quote_currency: str, on_date: date) -> Optional[FxRate]:
        raise NotImplementedError

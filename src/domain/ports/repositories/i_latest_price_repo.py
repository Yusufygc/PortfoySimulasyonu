from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Iterable, Sequence

from src.domain.models.latest_price import LatestPrice


class ILatestPriceRepository(ABC):
    """Repository contract for latest/intraday UI prices."""

    @abstractmethod
    def get_latest_prices(self, stock_ids: Sequence[int]) -> Dict[int, LatestPrice]:
        raise NotImplementedError

    @abstractmethod
    def get_latest_price_map(self, stock_ids: Sequence[int]) -> Dict[int, Decimal]:
        raise NotImplementedError

    @abstractmethod
    def upsert_latest_prices(self, prices: Iterable[LatestPrice]) -> None:
        raise NotImplementedError

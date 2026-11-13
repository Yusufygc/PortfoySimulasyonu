from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Dict, List, Optional

from src.domain.models.market_corporate_action import MarketActionStatus, MarketCorporateAction


class IMarketCorporateActionRepository(ABC):
    """Piyasa geçmişi (DuckDB) tarafındaki ticker bazlı kurumsal aksiyon deposu."""

    @abstractmethod
    def list_actions(
        self,
        ticker: Optional[str] = None,
        status: Optional[MarketActionStatus] = None,
    ) -> List[MarketCorporateAction]:
        """Tarihe göre sıralı olaylar. Depo yoksa boş liste döner."""
        raise NotImplementedError

    @abstractmethod
    def active_actions_by_ticker(self) -> Dict[str, List[MarketCorporateAction]]:
        """Yalnızca ONAYLI olaylar (ticker -> olaylar)."""
        raise NotImplementedError

    @abstractmethod
    def upsert(self, action: MarketCorporateAction) -> None:
        """(ticker, effective_date) anahtarıyla ekler veya günceller."""
        raise NotImplementedError

    @abstractmethod
    def set_status(self, ticker: str, effective_date: date, status: MarketActionStatus) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete(self, ticker: str, effective_date: date) -> bool:
        raise NotImplementedError

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from src.domain.models.split_event import SplitEvent, SplitLedgerSnapshot


class ISplitLedgerRepository(ABC):
    """Bölünmenin defterlere uygulanması ve geri alınması; her çağrı tek veritabanı işleminde ya tamamen uygulanır
    ya da hiç uygulanmaz."""

    @abstractmethod
    def load_snapshot(self, stock_id: Optional[int] = None, asset_id: Optional[int] = None) -> SplitLedgerSnapshot:
        """Hissenin (stock_id) ana ve model portföy işlemleri ya da varlığın (asset_id) işlemleri."""
        raise NotImplementedError

    @abstractmethod
    def apply(self, event: SplitEvent) -> SplitEvent:
        """Olayı, işlem değişikliklerini ve küsurat nakdini tek işlemde yazar; id'leri dolu olayı döner."""
        raise NotImplementedError

    @abstractmethod
    def revert(self, event_id: int) -> SplitEvent:
        """İşlemleri önceki değerlerine döndürür, küsurat nakdini siler, olayı REVERTED yapar (tek işlem)."""
        raise NotImplementedError

    @abstractmethod
    def get_event(self, event_id: int) -> Optional[SplitEvent]:
        raise NotImplementedError

    @abstractmethod
    def list_events(self, ticker: Optional[str] = None) -> List[SplitEvent]:
        raise NotImplementedError

    @abstractmethod
    def set_corporate_action(self, event_id: int, corporate_action_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def record_price_adjustment(
        self, event_id: int, before_date: Optional[date], count: int, market_effective_date: Optional[date]
    ) -> None:
        """Fiyat geçmişi düzeltmesinin kapsamını kaydeder (geri alma için)."""
        raise NotImplementedError

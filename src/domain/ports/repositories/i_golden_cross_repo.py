"""Golden Cross olay repository port arayüzü."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Iterable, List, Optional

from src.domain.models.golden_cross_event import CrossType, GoldenCrossEvent


class IGoldenCrossRepository(ABC):
    """Golden / Death Cross olay kalıcı katmanı."""

    @abstractmethod
    def upsert_events_bulk(self, events: Iterable[GoldenCrossEvent]) -> int:
        """Toplu upsert (ticker+cross_date+cross_type unique). Yeni eklenen satır sayısını döner."""
        raise NotImplementedError

    @abstractmethod
    def get_recent_events(
        self,
        since: date,
        cross_type: Optional[CrossType] = None,
        limit: int = 200,
    ) -> List[GoldenCrossEvent]:
        """since tarihinden bugüne kadar, opsiyonel tip filtresi ile, en yeni önce."""
        raise NotImplementedError

    @abstractmethod
    def get_events_for_ticker(self, ticker: str) -> List[GoldenCrossEvent]:
        """Tek hisse için tüm tarihçe, en yeni önce. `.IS` uzantısı verilse de verilmese de çalışır."""
        raise NotImplementedError

    @abstractmethod
    def get_last_cross_date_for_ticker(self, ticker: str) -> Optional[date]:
        """İncremental scan için: son kayıtlı cross tarihi (yoksa None)."""
        raise NotImplementedError

    @abstractmethod
    def delete_all(self) -> int:
        """Tüm cross eventlerini sil (full rescan için). Silinen satır sayısı."""
        raise NotImplementedError

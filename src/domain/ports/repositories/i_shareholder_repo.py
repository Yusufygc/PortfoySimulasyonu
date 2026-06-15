"""KAP ortaklık yapısı repository port arayüzü."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from src.domain.models.shareholder import ShareholderSnapshot


class IShareholderRepository(ABC):
    """KAP pay sahipliği tarihçesi kalıcı katmanı."""

    @abstractmethod
    def upsert_company(self, ticker: str, mkk_member_oid: str, title: Optional[str]) -> int:
        """Şirket kaydet/güncelle; satır id'sini döndür."""
        raise NotImplementedError

    @abstractmethod
    def replace_shareholder_history(
        self,
        ticker: str,
        snapshots: list[ShareholderSnapshot],
    ) -> None:
        """Verilen ticker için pay sahipliği tarihçesini tam olarak değiştir (atomik)."""
        raise NotImplementedError

    @abstractmethod
    def get_shareholder_history(self, ticker: str) -> list[ShareholderSnapshot]:
        """Saklı tarihçeyi döndür (en yeni önce). Yoksa boş liste."""
        raise NotImplementedError

    @abstractmethod
    def get_last_fetched_at(self, ticker: str) -> Optional[datetime]:
        """Verinin son çekildiği zaman; cache TTL kontrolü için."""
        raise NotImplementedError

    @abstractmethod
    def get_mkk_oid(self, ticker: str) -> Optional[str]:
        """Önceden saklı KAP OID; yoksa None."""
        raise NotImplementedError

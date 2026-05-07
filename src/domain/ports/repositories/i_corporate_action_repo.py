# src/domain/ports/repositories/i_corporate_action_repo.py

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.corporate_action import CorporateAction


class ICorporateActionRepository(ABC):
    """
    Kurumsal işlem (bedelli/bedelsiz sermaye artırımı) verilerine erişim soyut arayüzü.
    """

    @abstractmethod
    def get_by_id(self, action_id: int) -> Optional[CorporateAction]:
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> List[CorporateAction]:
        raise NotImplementedError

    @abstractmethod
    def get_by_stock(self, stock_id: int) -> List[CorporateAction]:
        raise NotImplementedError

    @abstractmethod
    def get_pending_by_stock(self, stock_id: int) -> List[CorporateAction]:
        """Belirli hisse için henüz uygulanmamış aksiyonları döner."""
        raise NotImplementedError

    @abstractmethod
    def get_all_pending(self) -> List[CorporateAction]:
        """Tüm hisseler için henüz uygulanmamış aksiyonları döner."""
        raise NotImplementedError

    @abstractmethod
    def insert(self, action: CorporateAction) -> CorporateAction:
        """Yeni aksiyon kaydeder; DB tarafından üretilen id ile döner."""
        raise NotImplementedError

    @abstractmethod
    def mark_applied(self, action_id: int) -> None:
        """applied=True, applied_at=now() olarak günceller."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, action_id: int) -> None:
        """Henüz uygulanmamış aksiyonu siler."""
        raise NotImplementedError

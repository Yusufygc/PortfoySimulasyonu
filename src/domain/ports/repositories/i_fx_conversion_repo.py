from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.fx_conversion import FxConversion


class IFxConversionRepository(ABC):
    @abstractmethod
    def add(self, conversion: FxConversion) -> FxConversion:
        raise NotImplementedError

    @abstractmethod
    def get(self, conversion_id: int) -> Optional[FxConversion]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> List[FxConversion]:
        """Tarih ve saat sırasına göre (eskiden yeniye)."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, conversion_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_all(self) -> None:
        raise NotImplementedError

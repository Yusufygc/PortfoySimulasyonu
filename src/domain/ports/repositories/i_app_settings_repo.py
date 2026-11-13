from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class IAppSettingsRepository(ABC):
    """Küçük anahtar-değer ayarları (ücret oranları vb.); veritabanında tutulduğundan yedeğe ve sıfırlamaya dahildir."""

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        ...

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        ...

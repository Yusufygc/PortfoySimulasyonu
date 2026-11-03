from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class IAssetSymbolVerifier(ABC):
    """Bir fiyat sembolünün çevrimiçi kaynakta geçerli olup olmadığını denetler."""

    @abstractmethod
    def verify(self, yf_symbol: str) -> bool:
        """Sembol için fiyat verisi varsa True. Ağ hatalarında False yerine istisna yükseltilebilir."""
        raise NotImplementedError

    def currency_of(self, yf_symbol: str) -> Optional[str]:
        """Sembolün işlem gördüğü para birimi (ör. `USD`, `TRY`, `EUR`); kaynak bildirmezse `None`."""
        return None

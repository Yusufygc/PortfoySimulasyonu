"""KAP ortaklık yapısı sağlayıcı port arayüzü."""
from __future__ import annotations

from typing import Protocol

from src.domain.models.shareholder import ShareholderSnapshot


class ShareholderProviderUnavailable(RuntimeError):
    """KAP veri kaynağı kullanılamaz olduğunda fırlatılır."""


class IShareholderProvider(Protocol):
    """Port: KAP pay sahipliği tarihçesi sağlayıcısı."""

    def get_shareholder_history(self, ticker: str) -> list[ShareholderSnapshot]:
        """
        Ticker için pay sahipliği tarihçesini döndür (en yeni önce).

        Raises:
            ShareholderProviderUnavailable: ağ/parse hatası ya da ticker bulunamadı.
        """
        ...

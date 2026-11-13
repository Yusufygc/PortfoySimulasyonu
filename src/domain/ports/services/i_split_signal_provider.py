from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import List, NamedTuple, Optional, Sequence

from src.domain.models.split_signal import SplitSignal


class SplitTarget(NamedTuple):
    """Bölünme taranacak sembol: uygulamadaki anahtar (BIST kodu veya varlık sembolü), Yahoo sembolü ve defter
    bağlantıları. `stock_id` BIST hissesinde, `asset_id` Portföyüm varlığında doludur."""
    key: str
    yf_symbol: str
    stock_id: Optional[int] = None
    asset_id: Optional[int] = None


class ISplitSignalProvider(ABC):
    """Bir kaynaktan (Yahoo, KAP, fiyat kırılması) bölünme sinyali toplar. Kaynak erişilemezse boş liste döner
    ve loglar; tek kaynağın hatası tüm taramayı durdurmaz."""

    @abstractmethod
    def fetch_signals(self, targets: Sequence[SplitTarget], since: date) -> List[SplitSignal]:
        raise NotImplementedError

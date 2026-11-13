from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from src.domain.models.ledger import LedgerSnapshot


class ILedgerReader(ABC):
    """Üç işlem defterinin tek okuma noktası (tek veritabanı oturumu)."""

    @abstractmethod
    def snapshot(
        self, stock_id: Optional[int] = None, asset_id: Optional[int] = None, include_assets: bool = False,
    ) -> LedgerSnapshot:
        """`stock_id` verilirse o hissenin ana ve model portföy lotları; `asset_id` verilirse o varlığın lotları;
        ikisi de yoksa tüm hisselerin ana ve model portföy lotları (`include_assets` ile varlık defteri de)."""
        raise NotImplementedError

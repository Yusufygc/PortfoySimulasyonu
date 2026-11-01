from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.asset_trade import AssetTrade


class IAssetTradeRepository(ABC):
    """Varlık defteri işlem kayıtları."""

    @abstractmethod
    def add_trade(self, trade: AssetTrade) -> AssetTrade:
        raise NotImplementedError

    @abstractmethod
    def get_trade(self, trade_id: int) -> Optional[AssetTrade]:
        raise NotImplementedError

    @abstractmethod
    def list_trades(self, asset_id: Optional[int] = None) -> List[AssetTrade]:
        """Tarih, saat ve id sırasıyla işlemler; `asset_id` verilirse yalnızca o varlığınkiler."""
        raise NotImplementedError

    @abstractmethod
    def delete_trade(self, trade_id: int) -> None:
        raise NotImplementedError

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.asset import Asset, AssetClass


class IAssetRepository(ABC):
    """BIST dışı varlık tanımlarının deposu."""

    @abstractmethod
    def add_asset(self, asset: Asset) -> Asset:
        """Yeni varlığı kaydeder; `(asset_class, symbol)` çakışırsa `ValueError` fırlatır."""
        raise NotImplementedError

    @abstractmethod
    def get_asset(self, asset_id: int) -> Optional[Asset]:
        raise NotImplementedError

    @abstractmethod
    def get_asset_by_symbol(self, asset_class: AssetClass, symbol: str) -> Optional[Asset]:
        raise NotImplementedError

    @abstractmethod
    def list_assets(self, active_only: bool = True) -> List[Asset]:
        raise NotImplementedError

    @abstractmethod
    def set_active(self, asset_id: int, is_active: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_asset(self, asset_id: int) -> None:
        """Varlığı ve (cascade ile) işlem/fiyat kayıtlarını siler."""
        raise NotImplementedError

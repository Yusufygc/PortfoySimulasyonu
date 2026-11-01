# src/domain/models/asset.py

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AssetClass(str, Enum):
    """BIST dışı varlık sınıfları. BIST hisseleri ayrı defterde (trades/stocks) tutulur."""

    US_STOCK = "US_STOCK"
    CRYPTO = "CRYPTO"
    PRECIOUS_METAL = "PRECIOUS_METAL"


class AssetUnit(str, Enum):
    """Miktarın birimi. Fiyat birimi `Asset.quote_currency` ile belirtilir."""

    UNIT = "UNIT"    # adet (hisse, kripto)
    GRAM = "GRAM"
    OUNCE = "OUNCE"  # troy ons


@dataclass(frozen=True)
class Asset:
    """
    Portföyde takip edilen BIST dışı bir varlık (ABD hissesi, kripto, kıymetli maden).

    - symbol: kullanıcıya gösterilen sembol (örn. AAPL, BTC, XAU)
    - yf_symbol: fiyat sağlayıcıya olduğu gibi verilen sembol (örn. AAPL, BTC-USD, GC=F)
    - quote_currency: fiyatın para birimi (USD, TRY ...)
    """

    id: Optional[int]
    symbol: str
    name: str
    asset_class: AssetClass
    quote_currency: str
    yf_symbol: str
    unit: AssetUnit = AssetUnit.UNIT
    is_active: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.asset_class, AssetClass):
            try:
                object.__setattr__(self, "asset_class", AssetClass(self.asset_class))
            except ValueError as exc:
                raise ValueError(f"Unknown asset class: {self.asset_class}") from exc
        if not isinstance(self.unit, AssetUnit):
            try:
                object.__setattr__(self, "unit", AssetUnit(self.unit))
            except ValueError as exc:
                raise ValueError(f"Unknown asset unit: {self.unit}") from exc

        symbol = (self.symbol or "").strip().upper()
        if not symbol:
            raise ValueError("Asset symbol is required")
        object.__setattr__(self, "symbol", symbol)

        name = (self.name or "").strip()
        if not name:
            raise ValueError("Asset name is required")
        object.__setattr__(self, "name", name)

        currency = (self.quote_currency or "").strip().upper()
        if len(currency) != 3:
            raise ValueError("Asset quote currency must be a 3 letter code")
        object.__setattr__(self, "quote_currency", currency)

        yf_symbol = (self.yf_symbol or "").strip()
        if not yf_symbol:
            raise ValueError("Asset price symbol is required")
        object.__setattr__(self, "yf_symbol", yf_symbol)

    @property
    def is_try_quoted(self) -> bool:
        return self.quote_currency == "TRY"

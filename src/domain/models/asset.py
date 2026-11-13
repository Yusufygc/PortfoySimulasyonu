# src/domain/models/asset.py

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional

from src.domain.units import ounce_price_to_gram_price


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
    trade_currency: str = ""   # işlemin ödendiği nakit para birimi; boşsa fiyat para birimi (altın gram: fiyat USD, işlem TRY)

    def __post_init__(self) -> None:
        self._coerce_enum("asset_class", AssetClass, "asset class")
        self._coerce_enum("unit", AssetUnit, "asset unit")
        self._set_required("symbol", "Asset symbol is required", str.upper)
        self._set_required("name", "Asset name is required")
        self._set_required("yf_symbol", "Asset price symbol is required")
        self._set_required("quote_currency", "Asset quote currency must be a 3 letter code", str.upper, length=3)
        trade = (self.trade_currency or "").strip().upper()
        if trade and len(trade) != 3:
            raise ValueError("Asset trade currency must be a 3 letter code")
        object.__setattr__(self, "trade_currency", trade)

    def _coerce_enum(self, field_name: str, enum_type, label: str) -> None:
        value = getattr(self, field_name)
        if isinstance(value, enum_type):
            return
        try:
            object.__setattr__(self, field_name, enum_type(value))
        except ValueError as exc:
            raise ValueError(f"Unknown {label}: {value}") from exc

    def _set_required(self, field_name: str, message: str, transform=None, length: Optional[int] = None) -> None:
        value = (getattr(self, field_name) or "").strip()
        if transform is not None:
            value = transform(value)
        if not value or (length is not None and len(value) != length):
            raise ValueError(message)
        object.__setattr__(self, field_name, value)

    @property
    def settlement_currency(self) -> str:
        """İşlemin ödendiği/tahsil edildiği nakit para birimi (ortak havuzdaki bakiye); işlem fiyatı bu birimdedir."""
        return self.trade_currency or self.quote_currency

    @property
    def is_try_settled(self) -> bool:
        return self.settlement_currency == "TRY"

    @property
    def is_try_quoted(self) -> bool:
        return self.quote_currency == "TRY"

    def unit_price(self, quoted_price: Decimal) -> Decimal:
        """Sağlayıcının verdiği fiyatı varlığın birimine çevirir.

        Kıymetli maden vadeli kontratları ons başına fiyat verir; gram birimli varlık için gram fiyatına çevrilir.
        """
        if self.asset_class == AssetClass.PRECIOUS_METAL and self.unit == AssetUnit.GRAM:
            return ounce_price_to_gram_price(quoted_price)
        return quoted_price

# src/domain/models/asset_price.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


def _positive_decimal(value, field_name: str) -> Decimal:
    if isinstance(value, float):
        raise TypeError(f"{field_name} must not be a float; use Decimal or str")
    number = value if isinstance(value, Decimal) else Decimal(str(value))
    if number <= 0:
        raise ValueError(f"{field_name} must be positive")
    return number


def _required_text(value: str, field_name: str) -> str:
    text = (value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


@dataclass(frozen=True)
class AssetQuote:
    """Sağlayıcıdan gelen anlık fiyat: sembol, fiyat ve bar zamanı (saat dilimsiz, UTC)."""

    symbol: str
    price: Decimal
    as_of: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", _required_text(self.symbol, "symbol"))
        object.__setattr__(self, "price", _positive_decimal(self.price, "price"))


@dataclass(frozen=True)
class AssetPrice:
    """Varlığın günlük kapanış fiyatı (varlığın kendi para biriminde)."""

    id: Optional[int]
    asset_id: int
    price_date: date
    close_price: Decimal
    currency_code: str
    source: str

    def __post_init__(self) -> None:
        if self.asset_id <= 0:
            raise ValueError("Asset id must be positive")
        object.__setattr__(self, "close_price", _positive_decimal(self.close_price, "close_price"))
        object.__setattr__(self, "currency_code", _required_text(self.currency_code, "currency_code").upper())
        object.__setattr__(self, "source", _required_text(self.source, "source"))


@dataclass(frozen=True)
class AssetLatestPrice:
    """Varlığın son (gün içi olabilir) fiyatı; rapor ve backtest için kullanılmaz."""

    id: Optional[int]
    asset_id: int
    price: Decimal
    currency_code: str
    as_of: datetime
    source: str
    fetched_at: datetime

    def __post_init__(self) -> None:
        if self.asset_id <= 0:
            raise ValueError("Asset id must be positive")
        object.__setattr__(self, "price", _positive_decimal(self.price, "price"))
        object.__setattr__(self, "currency_code", _required_text(self.currency_code, "currency_code").upper())
        object.__setattr__(self, "source", _required_text(self.source, "source"))


@dataclass(frozen=True)
class FxRate:
    """Kur kaydı: 1 birim `base_currency` kaç `quote_currency` eder (örn. USD/TRY = 34.5)."""

    id: Optional[int]
    base_currency: str
    quote_currency: str
    rate_date: date
    rate: Decimal
    source: str

    def __post_init__(self) -> None:
        base = _required_text(self.base_currency, "base_currency").upper()
        quote = _required_text(self.quote_currency, "quote_currency").upper()
        if base == quote:
            raise ValueError("FX base and quote currencies must differ")
        object.__setattr__(self, "base_currency", base)
        object.__setattr__(self, "quote_currency", quote)
        object.__setattr__(self, "rate", _positive_decimal(self.rate, "rate"))
        object.__setattr__(self, "source", _required_text(self.source, "source"))

    @property
    def pair(self) -> str:
        return f"{self.base_currency}{self.quote_currency}"

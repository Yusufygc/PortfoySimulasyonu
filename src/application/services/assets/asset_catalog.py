"""Hazır varlık kataloğu: tek tıkla eklenebilen kıymetli maden ve kripto varlıkları.

ABD hisseleri (NASDAQ/NYSE) katalogda yoktur; kullanıcı sembolle ekler ve sembol çevrimiçi doğrulanır.
Kıymetli madenler vadeli kontrat fiyatıyla (USD/troy ons) izlenir; spot fiyattan küçük sapma gösterebilir.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from src.domain.models.asset import AssetClass, AssetUnit


@dataclass(frozen=True)
class CatalogEntry:
    key: str
    name: str
    asset_class: AssetClass
    quote_currency: str
    yf_symbol: str
    unit: AssetUnit


ASSET_CATALOG: Tuple[CatalogEntry, ...] = (
    CatalogEntry("XAU", "Altın (ons)", AssetClass.PRECIOUS_METAL, "USD", "GC=F", AssetUnit.OUNCE),
    CatalogEntry("XAG", "Gümüş (ons)", AssetClass.PRECIOUS_METAL, "USD", "SI=F", AssetUnit.OUNCE),
    CatalogEntry("XPT", "Platin (ons)", AssetClass.PRECIOUS_METAL, "USD", "PL=F", AssetUnit.OUNCE),
    CatalogEntry("XPD", "Paladyum (ons)", AssetClass.PRECIOUS_METAL, "USD", "PA=F", AssetUnit.OUNCE),
    CatalogEntry("BTC", "Bitcoin", AssetClass.CRYPTO, "USD", "BTC-USD", AssetUnit.UNIT),
    CatalogEntry("ETH", "Ethereum", AssetClass.CRYPTO, "USD", "ETH-USD", AssetUnit.UNIT),
    CatalogEntry("SOL", "Solana", AssetClass.CRYPTO, "USD", "SOL-USD", AssetUnit.UNIT),
    CatalogEntry("XRP", "XRP", AssetClass.CRYPTO, "USD", "XRP-USD", AssetUnit.UNIT),
)


def find_catalog_entry(key: str) -> Optional[CatalogEntry]:
    wanted = (key or "").strip().upper()
    return next((entry for entry in ASSET_CATALOG if entry.key == wanted), None)

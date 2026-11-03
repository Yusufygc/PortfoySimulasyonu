"""Hazır varlık kataloğu: tek tıkla eklenebilen kıymetli maden (altın, gümüş, platin), kripto ve popüler NASDAQ hisseleri.

Katalogda olmayan ABD hissesini ve kriptoyu kullanıcı sembolle ekler; sembol ve para birimi çevrimiçi doğrulanır.
Kıymetli madenler vadeli kontrat fiyatıyla (USD/troy ons) izlenir ve gram birimine çevrilir; gram alım-satım TL ile
yapılır (TL nakitten ödenir, fiyat ons x USDTRY / 31,1035). Spot fiyattan küçük sapma gösterebilir.
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
    trade_currency: str = ""   # boşsa fiyat para birimi


ASSET_CATALOG: Tuple[CatalogEntry, ...] = (
    CatalogEntry("XAU", "Altın (gram)", AssetClass.PRECIOUS_METAL, "USD", "GC=F", AssetUnit.GRAM, "TRY"),
    CatalogEntry("XAG", "Gümüş (gram)", AssetClass.PRECIOUS_METAL, "USD", "SI=F", AssetUnit.GRAM, "TRY"),
    CatalogEntry("XPT", "Platin (gram)", AssetClass.PRECIOUS_METAL, "USD", "PL=F", AssetUnit.GRAM, "TRY"),
    CatalogEntry("BTC", "Bitcoin", AssetClass.CRYPTO, "USD", "BTC-USD", AssetUnit.UNIT),
    CatalogEntry("ETH", "Ethereum", AssetClass.CRYPTO, "USD", "ETH-USD", AssetUnit.UNIT),
    CatalogEntry("SOL", "Solana", AssetClass.CRYPTO, "USD", "SOL-USD", AssetUnit.UNIT),
    CatalogEntry("XRP", "XRP", AssetClass.CRYPTO, "USD", "XRP-USD", AssetUnit.UNIT),
    CatalogEntry("AAPL", "Apple", AssetClass.US_STOCK, "USD", "AAPL", AssetUnit.UNIT),
    CatalogEntry("MSFT", "Microsoft", AssetClass.US_STOCK, "USD", "MSFT", AssetUnit.UNIT),
    CatalogEntry("NVDA", "NVIDIA", AssetClass.US_STOCK, "USD", "NVDA", AssetUnit.UNIT),
    CatalogEntry("AMZN", "Amazon", AssetClass.US_STOCK, "USD", "AMZN", AssetUnit.UNIT),
    CatalogEntry("GOOGL", "Alphabet (Google)", AssetClass.US_STOCK, "USD", "GOOGL", AssetUnit.UNIT),
    CatalogEntry("META", "Meta Platforms", AssetClass.US_STOCK, "USD", "META", AssetUnit.UNIT),
    CatalogEntry("TSLA", "Tesla", AssetClass.US_STOCK, "USD", "TSLA", AssetUnit.UNIT),
    CatalogEntry("AVGO", "Broadcom", AssetClass.US_STOCK, "USD", "AVGO", AssetUnit.UNIT),
    CatalogEntry("NFLX", "Netflix", AssetClass.US_STOCK, "USD", "NFLX", AssetUnit.UNIT),
    CatalogEntry("AMD", "AMD", AssetClass.US_STOCK, "USD", "AMD", AssetUnit.UNIT),
    CatalogEntry("COST", "Costco", AssetClass.US_STOCK, "USD", "COST", AssetUnit.UNIT),
    CatalogEntry("ADBE", "Adobe", AssetClass.US_STOCK, "USD", "ADBE", AssetUnit.UNIT),
    CatalogEntry("PEP", "PepsiCo", AssetClass.US_STOCK, "USD", "PEP", AssetUnit.UNIT),
    CatalogEntry("CSCO", "Cisco", AssetClass.US_STOCK, "USD", "CSCO", AssetUnit.UNIT),
    CatalogEntry("INTC", "Intel", AssetClass.US_STOCK, "USD", "INTC", AssetUnit.UNIT),
    CatalogEntry("QCOM", "Qualcomm", AssetClass.US_STOCK, "USD", "QCOM", AssetUnit.UNIT),
    CatalogEntry("TXN", "Texas Instruments", AssetClass.US_STOCK, "USD", "TXN", AssetUnit.UNIT),
    CatalogEntry("AMAT", "Applied Materials", AssetClass.US_STOCK, "USD", "AMAT", AssetUnit.UNIT),
    CatalogEntry("PYPL", "PayPal", AssetClass.US_STOCK, "USD", "PYPL", AssetUnit.UNIT),
    CatalogEntry("SBUX", "Starbucks", AssetClass.US_STOCK, "USD", "SBUX", AssetUnit.UNIT),
    CatalogEntry("MU", "Micron", AssetClass.US_STOCK, "USD", "MU", AssetUnit.UNIT),
    CatalogEntry("ASML", "ASML", AssetClass.US_STOCK, "USD", "ASML", AssetUnit.UNIT),
    CatalogEntry("PLTR", "Palantir", AssetClass.US_STOCK, "USD", "PLTR", AssetUnit.UNIT),
    CatalogEntry("QQQ", "Invesco QQQ (Nasdaq-100 ETF)", AssetClass.US_STOCK, "USD", "QQQ", AssetUnit.UNIT),
)


def find_catalog_entry(key: str) -> Optional[CatalogEntry]:
    wanted = (key or "").strip().upper()
    return next((entry for entry in ASSET_CATALOG if entry.key == wanted), None)

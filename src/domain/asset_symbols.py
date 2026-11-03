"""BIST dışı varlıklar için fiyat sembolü çözümleme (sınıfa duyarlı).

BIST hisseleri `src/domain/ticker.py` (`to_yf_symbol`, `.IS` eki) ile çözülür; bu modül `.IS` eklemez.
Varlık defterindeki sembol, fiyat sağlayıcıya olduğu gibi (`Asset.yf_symbol`) verilir.
"""
from __future__ import annotations

import re

from src.domain.models.asset import AssetClass

_EXPLICIT_MARKERS = "-=."  # BTC-USD, GC=F, BRK.B: kullanıcı tam sembol vermiş
_VALID_SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9.\-=]{0,19}$")
_SHARE_CLASS = re.compile(r"^[A-Z]{1,5}\.([A-Z])$")  # BRK.B: tek harfli hisse sınıfı (borsa eki .AS, .IS gibi 2+ harftir)


def resolve_yf_symbol(asset_class: AssetClass, symbol: str) -> str:
    """Kullanıcının girdiği sembolden fiyat sağlayıcı sembolünü üretir.

    - Tam sembol (`BTC-USD`, `GC=F`) olduğu gibi (büyük harf) döner; `BRK.B` gibi tek harfli hisse sınıfı Yahoo'nun
      `BRK-B` yazımına çevrilir.
    - Kripto için yalın kod (`BTC`) USD paritesine çevrilir (`BTC-USD`).
    - ABD hissesi ve diğerleri büyük harfe çevrilir; `.IS` eki eklenmez.
    - Boşluk, virgül gibi karakterler (çoklu sembol) ve endeksler (`^IXIC`) reddedilir.
    """
    cleaned = (symbol or "").strip().upper()
    if not cleaned:
        raise ValueError("Asset symbol is required")
    if cleaned.startswith("^"):
        raise ValueError("Endeks doğrudan alınamaz; onu izleyen bir ETF kullanın (ör. QQQ)")
    if not _VALID_SYMBOL.match(cleaned):
        raise ValueError("Sembol yalnızca harf, rakam ve . - = karakterlerinden oluşmalı (tek sembol)")
    share_class = _SHARE_CLASS.match(cleaned)
    if share_class and asset_class == AssetClass.US_STOCK:
        return cleaned.replace(".", "-")
    if any(marker in cleaned for marker in _EXPLICIT_MARKERS):
        return cleaned
    if asset_class == AssetClass.CRYPTO:
        return f"{cleaned}-USD"
    return cleaned

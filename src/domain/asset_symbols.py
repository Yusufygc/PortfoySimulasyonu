"""BIST dışı varlıklar için fiyat sembolü çözümleme (sınıfa duyarlı).

BIST hisseleri `src/domain/ticker.py` (`to_yf_symbol`, `.IS` eki) ile çözülür; bu modül `.IS` eklemez.
Varlık defterindeki sembol, fiyat sağlayıcıya olduğu gibi (`Asset.yf_symbol`) verilir.
"""
from __future__ import annotations

from src.domain.models.asset import AssetClass

_EXPLICIT_MARKERS = "-=^."  # BTC-USD, GC=F, ^IXIC, BRK.B: kullanıcı tam sembol vermiş


def resolve_yf_symbol(asset_class: AssetClass, symbol: str) -> str:
    """Kullanıcının girdiği sembolden fiyat sağlayıcı sembolünü üretir.

    - Tam sembol (`BTC-USD`, `GC=F`, `^IXIC`, `BRK.B`) olduğu gibi (büyük harf) döner.
    - Kripto için yalın kod (`BTC`) USD paritesine çevrilir (`BTC-USD`).
    - ABD hissesi ve diğerleri büyük harfe çevrilir; `.IS` eki eklenmez.
    """
    cleaned = (symbol or "").strip().upper()
    if not cleaned:
        raise ValueError("Asset symbol is required")
    if any(marker in cleaned for marker in _EXPLICIT_MARKERS):
        return cleaned
    if asset_class == AssetClass.CRYPTO:
        return f"{cleaned}-USD"
    return cleaned

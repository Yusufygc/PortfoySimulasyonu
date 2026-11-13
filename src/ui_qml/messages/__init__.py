"""Python tarafından üretilen kullanıcı metinleri için tek katalog (özellik başına modüller).

Denetleyiciler Türkçe metin yazmaz; `msg("anahtar", ad=değer)` çağırır. QML'in kendi metinleri `Strings.qml`'de kalır.
Anahtar adı: `<alan>.<olay>` (ör. `dividend.added`). Parametreler `str.format` ile doldurulur.
Yeni metin, anahtar önekinin modülüne eklenir (`portfolio.py`, `market.py` ...); yeni alan için `MODULES`'e bir satır.
Aynı anahtar iki modülde tanımlanırsa içe aktarma hata verir.
`tests/ui_qml/test_message_catalog.py` tanımsız ve kullanılmayan anahtarı yakalar.
"""
from __future__ import annotations

from typing import Dict, Iterable, Mapping

from . import portfolio, market, stock, model_portfolio, analysis, advisor, shell

MODULES = (portfolio, market, stock, model_portfolio, analysis, advisor, shell)


def merge_catalogs(parts: Iterable[Mapping[str, str]]) -> Dict[str, str]:
    """Modül kataloglarını birleştirir; aynı anahtar iki kez tanımlanırsa `ValueError`."""
    merged: Dict[str, str] = {}
    for part in parts:
        duplicates = sorted(set(merged) & set(part))
        if duplicates:
            raise ValueError(f"Mesaj anahtarı birden çok modülde tanımlı: {duplicates}")
        merged.update(part)
    return merged


MESSAGES: Dict[str, str] = merge_catalogs(module.MESSAGES for module in MODULES)


def msg(key: str, **params: object) -> str:
    """Anahtarın metnini döner; parametreler `{ad}` yer tutucularına yazılır."""
    template = MESSAGES[key]
    return template.format(**params) if params else template

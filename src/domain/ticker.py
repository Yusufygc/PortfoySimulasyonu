"""BIST ticker biçimi: depolamada ve süreç içinde kanonik biçim uzantısız büyük harftir (`THYAO`).

`.IS` uzantısı yalnızca yfinance gibi sembolün borsa son ekini isteyen dış sınırlarda eklenir (`to_yf_symbol`).
DuckDB piyasa geçmişi, KAP, İş Yatırım ve arayüz zaten uzantısız biçimi kullanır.
"""
from __future__ import annotations

_BIST_SUFFIX = ".IS"


def clean_ticker(ticker: str | None) -> str:
    """`THYAO.IS`, ` thyao ` -> `THYAO`. Boş girdi için boş metin döner."""
    value = (ticker or "").strip().upper()
    return value[: -len(_BIST_SUFFIX)] if value.endswith(_BIST_SUFFIX) else value


def to_yf_symbol(ticker: str | None) -> str:
    """yfinance sembolü: BIST kodlarına `.IS` ekler; endeks (`^XU100`), kur (`USDTRY=X`) ve zaten
    borsa son ekli semboller olduğu gibi (büyük harfe çevrilerek) kalır."""
    value = (ticker or "").strip().upper()
    if not value:
        return ""
    if value.startswith("^") or "=" in value or "." in value:
        return value
    return value + _BIST_SUFFIX

"""Kullanıcının yazdığı sayı metnini (Türkçe veya düz biçim) Decimal'e çevirir."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Optional

_THOUSANDS_ONLY = re.compile(r"^\d{1,3}(\.\d{3})+$")


def parse_decimal_text(text: str) -> Optional[Decimal]:
    """'1.234,56' -> 1234.56, '50.000' -> 50000 (nokta binlik ayracı), '1234.56' -> 1234.56, '25,5' -> 25.5.

    Boş, sayı olmayan veya sonlu olmayan (nan/inf) metin için None döner.
    """
    raw = (text or "").strip().replace(" ", "")
    if not raw:
        return None
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif _THOUSANDS_ONLY.match(raw):
        raw = raw.replace(".", "")
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None
    return value if value.is_finite() else None

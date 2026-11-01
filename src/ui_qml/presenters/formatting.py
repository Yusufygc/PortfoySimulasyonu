"""Türkçe sayı, para ve yüzde biçimleyicileri (tek kopya).

Denetleyicilerde `_fmt_tr`, `_fmt_money`, `_fmt_pct`, `_fmt_currency` adıyla dağınık duran kopyaların yerini alır.
Binlik ayraç nokta, ondalık ayraç virgüldür: `1.234,50`, `1.234,50 ₺`, `%12,34`, `+%1,07`.
"""
from __future__ import annotations

import math
from decimal import Decimal
from typing import Optional, Union

Number = Union[int, float, Decimal]

_SWAP_SEPARATORS = str.maketrans({",": ".", ".": ","})
ZERO_MONEY = "0,00 ₺"
ZERO_PCT = "%0,00"
_ZERO_PCT_EPSILON = 0.0001  # bunun altı sıfır kabul edilir ("-%0,00" görünmesin)


def tr_number(value: Number, decimals: int = 2) -> str:
    """1234.5 -> '1.234,50'. Decimal tam kalır, diğer sayılar olduğu gibi biçimlenir."""
    return f"{value:,.{decimals}f}".translate(_SWAP_SEPARATORS)


def tr_money(value: Optional[Number]) -> str:
    """1234.5 -> '1.234,50 ₺'; None -> '0,00 ₺'; negatifte '-62.608,18 ₺'. Sayıya çevrilemezse metin aynen yazılır."""
    if value is None:
        return ZERO_MONEY
    try:
        number = value if isinstance(value, Decimal) else float(value)
        return f"{tr_number(number)} ₺"
    except (TypeError, ValueError):
        return f"{value} ₺"


def tr_pct(value: Optional[Number], with_sign: bool = False) -> str:
    """12.345 -> '%12,35'. Eksi her zaman yazılır ('-%1,20'); artı yalnızca with_sign ile ('+%1,20').

    None, sonsuz/NaN ve mutlak değeri 0,0001'den küçük değerler '%0,00' döner.
    """
    if value is None:
        return ZERO_PCT
    try:
        number = float(value)
    except (TypeError, ValueError):
        return f"%{value}"
    if not math.isfinite(number) or abs(number) < _ZERO_PCT_EPSILON:
        return ZERO_PCT
    text = f"{abs(number):.2f}".replace(".", ",")
    if number < 0:
        return f"-%{text}"
    return f"+%{text}" if with_sign else f"%{text}"


def tr_number_or_dash(value: object, decimals: int = 2) -> str:
    """None -> '-'; sayıya çevrilemeyen değer metin olarak aynen döner."""
    if value is None:
        return "-"
    try:
        return tr_number(float(value), decimals)
    except (TypeError, ValueError):
        return str(value)

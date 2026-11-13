"""SQLite'ta `Numeric` sütun türü: float depolamasının değeri bozacağı yazmaları reddeder.

SQLite `Decimal` desteklemez; SQLAlchemy `Numeric` değerini `REAL` (IEEE 754 çift) olarak yazar ve okurken sütun
ölçeğine yuvarlar. Yaklaşık 15 anlamlı basamağı aşan değerler bu yüzden sessizce değişir. `ExactNumeric` aynı
DDL'i üretir (`NUMERIC(p, s)`, şema göçü gerekmez) ve bağlama anında "float üzerinden gidip ölçeğe yuvarlanan değer,
doğrudan ölçeğe yuvarlanan değerle aynı mı" denetler; aynı değilse yazmayı `ValueError` ile durdurur.
"""
from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Context, Decimal

from sqlalchemy import Numeric
from sqlalchemy.types import TypeDecorator

_CONTEXT = Context(prec=60, rounding=ROUND_HALF_EVEN)


class ExactNumeric(TypeDecorator):
    impl = Numeric
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None or dialect.name != "sqlite":
            return value
        number = value if isinstance(value, Decimal) else Decimal(str(value))
        if not number.is_finite():
            raise ValueError(f"Sonlu olmayan sayı kaydedilemez: {number}")
        scale = self.impl.scale
        if scale is None:
            return value
        quantum = Decimal(1).scaleb(-scale)
        intended = number.quantize(quantum, context=_CONTEXT)
        stored = Decimal(repr(float(number))).quantize(quantum, context=_CONTEXT)
        if intended != stored:
            raise ValueError(
                f"{number} değeri SQLite'ta float olarak saklanırken kesinlik kaybeder "
                f"(NUMERIC({self.impl.precision}, {scale}) için güvenli aralık ~15 anlamlı basamak)."
            )
        return value

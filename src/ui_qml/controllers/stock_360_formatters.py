"""
Stock 360 Formatters — Para birimi, fiyat, hacim ve grafik renk sabitleri.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from src.ui_qml.presenters.formatting import tr_number

# Renk paleti (Donut ve grafikler için)
DONUT_COLORS = [
    "#2962ff",  # Accent Mavi
    "#089981",  # Bullish Yeşil
    "#f59e0b",  # Amber / Turuncu
    "#8b5cf6",  # Mor
    "#ec4899",  # Pembe
    "#06b6d4",  # Camgöbeği
    "#64748b",  # Nötr Gri (Genellikle Halka Açık / Diğer)
]


def format_currency(val: Optional[float | Decimal]) -> str:
    """Finansal büyüklükleri Türk finans standardına (Mr / Mn / Bin / ₺) göre formatlar."""
    if val is None:
        return "—"
    v = float(val)
    abs_v = abs(v)
    if abs_v >= 1_000_000_000:
        return f"₺{tr_number(v / 1_000_000_000, 2)} Mr"
    elif abs_v >= 1_000_000:
        return f"₺{tr_number(v / 1_000_000, 2)} Mn"
    elif abs_v >= 1_000:
        return f"₺{tr_number(v, 2)}"
    return f"₺{tr_number(v, 2)}"


def format_price(val: Optional[float | Decimal]) -> str:
    """Fiyat formatlar (örn. ₺394.00)."""
    if val is None:
        return "₺0,00"
    return f"₺{tr_number(float(val), 2)}"


def format_volume(val: Optional[int | float]) -> str:
    """İşlem hacmini Türk finans standardına (Mr / Mn / Bin) göre formatlar."""
    if val is None or val == 0:
        return "0"
    v = float(val)
    abs_v = abs(v)
    if abs_v >= 1_000_000_000:
        return f"{tr_number(v / 1_000_000_000, 1)} Mr"
    elif abs_v >= 1_000_000:
        return f"{tr_number(v / 1_000_000, 1)} Mn"
    elif abs_v >= 1_000:
        return f"{tr_number(v / 1_000, 1)} Bin"
    return tr_number(int(v), 0)


_format_currency = format_currency
_format_price = format_price
_format_volume = format_volume

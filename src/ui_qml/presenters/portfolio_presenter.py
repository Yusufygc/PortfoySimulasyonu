"""Portföyüm sayfası sunum yardımcıları: birleşik özeti QML'in okuyacağı metin ve sözlüklere çevirir (saf fonksiyonlar)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from src.ui_qml.presenters.formatting import tr_number, tr_pct
from src.domain.models.unified_portfolio import (
    HUNDRED,
    AllocationClass,
    AllocationSlice,
    HoldingValuation,
    UnifiedSummary,
)

CURRENCY_SYMBOLS = {"TRY": "₺", "USD": "$", "EUR": "€"}

# Dağılım dilim renkleri (sınıf sabit renk taşır; sınıf eklenince/çıkınca renkler kaymaz)
CLASS_COLORS = {
    AllocationClass.BIST_STOCK: "#2962ff",
    AllocationClass.US_STOCK: "#089981",
    AllocationClass.CRYPTO: "#ff9800",
    AllocationClass.PRECIOUS_METAL: "#e91e63",
    AllocationClass.CASH: "#787b86",
}

# Sekme anahtarı -> sınıf (None: tüm pozisyonlar)
TAB_ALL = "ALL"
TAB_KEYS = (TAB_ALL, "BIST_STOCK", "US_STOCK", "CRYPTO", "PRECIOUS_METAL")


def format_money(amount: Decimal, currency: str = "TRY") -> str:
    """`₺1.234,56` / `$1.234,56`; bilinmeyen para birimi kodu sonek olur. Negatifte eksi simgeden önce: `-₺1.234,56`."""
    code = (currency or "TRY").upper()
    symbol = CURRENCY_SYMBOLS.get(code)
    number = tr_number(abs(amount))
    sign = "-" if amount < 0 and number.strip("0,.") else ""
    return f"{sign}{symbol}{number}" if symbol else f"{sign}{number} {code}"


def format_price(amount: Optional[Decimal], currency: str) -> str:
    """Birim fiyat: TL her zaman 2 hane (BIST adımı 0,01); küçük döviz/kripto fiyatları için 4 haneye kadar (0,0001 altında 8 hane)."""
    if amount is None:
        return "-"
    code = (currency or "TRY").upper()
    digits = 2 if code == "TRY" or abs(amount) >= 1 else (4 if abs(amount) >= Decimal("0.0001") else 8)
    symbol = CURRENCY_SYMBOLS.get(code)
    number = tr_number(amount, digits)
    return f"{symbol}{number}" if symbol else f"{number} {code}"


def format_quantity(quantity: Decimal) -> str:
    """Binlik ayraçlı, sondaki sıfırsız miktar (en çok 8 ondalık): 1.250, 0,5, 0,00012345."""
    text = tr_number(quantity, 8).rstrip("0").rstrip(",")
    return text or "0"


def format_pct(value: Optional[Decimal]) -> str:
    """İşaretli yüzde: `+%2,15`, `-%1,20`; bilinmiyorsa `-`."""
    if value is None:
        return "-"
    return tr_pct(value, with_sign=True)


def holding_row(holding: HoldingValuation, summary: UnifiedSummary) -> Dict[str, Any]:
    """Tek pozisyonun tablo satırı: tutarlar gösterim para biriminde, fiyat varlığın kendi para biriminde."""
    display = summary.display_currency
    cost_per_unit = holding.cost_native / holding.quantity if holding.quantity > 0 else Decimal("0")
    pl_pct = holding.unrealized_pl_pct
    return {
        "key": holding.key,
        "refId": holding.ref_id if holding.ref_id is not None else 0,
        "symbol": holding.symbol,
        "name": holding.name,
        "classKey": holding.allocation_class.value,
        "isBist": holding.allocation_class == AllocationClass.BIST_STOCK,
        "currency": holding.native_currency,
        "quantity": format_quantity(holding.quantity),
        "avgCost": format_price(cost_per_unit, holding.native_currency),
        "price": format_price(holding.price_native, holding.native_currency),
        "dailyChange": format_pct(holding.daily_change_pct),
        "isDailyUp": holding.daily_change_pct is not None and holding.daily_change_pct >= 0,
        "value": format_money(summary.display_amount(holding.value_try), display),
        "pl": format_money(summary.display_amount(holding.unrealized_pl_try), display),
        "plPct": format_pct(pl_pct),
        "isUp": holding.unrealized_pl_try >= 0,
        "weight": f"%{tr_number(holding.weight_pct, 1)}",
        "isPriced": holding.is_priced,
    }


def slice_dict(item: AllocationSlice, summary: UnifiedSummary) -> Dict[str, Any]:
    """Dağılım dilimi: `pct` 0-1 aralığında (donut açısı), `classKey` etiketi QML'de `Strings` çözer."""
    return {
        "classKey": item.allocation_class.value,
        "pct": float(round(item.weight_pct / HUNDRED, 4)),
        "color": CLASS_COLORS[item.allocation_class],
        "amount": format_money(summary.display_amount(item.value_try), summary.display_currency),
        "count": item.holdings_count,
    }


def filter_rows(summary: UnifiedSummary, tab_key: str) -> List[Dict[str, Any]]:
    """Sekmeye göre satırlar; `ALL` tüm pozisyonları (değere göre azalan) döner."""
    holdings = summary.holdings if tab_key == TAB_ALL else summary.holdings_of(AllocationClass(tab_key))
    return [holding_row(holding, summary) for holding in holdings]


def tab_counts(summary: UnifiedSummary) -> Dict[str, int]:
    counts = {key: len(summary.holdings_of(AllocationClass(key))) for key in TAB_KEYS if key != TAB_ALL}
    counts[TAB_ALL] = len(summary.holdings)
    return counts

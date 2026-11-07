"""Bölünme / bedelsiz uygulamasının lot ve fiyat hesabı (saf fonksiyonlar).

Kural (geriye dönük düzeltme): ex-date öncesi işlemlerin lotları çarpanla büyütülür, fiyatları işlem tutarı
korunacak şekilde küçültülür. Tam lotlu defterde (BIST) eldeki lot `floor(eldeki * çarpan)` olur; her işlemin
yeni lotu, işlem öncesi ve sonrası eldeki lotun yuvarlanmış karşılıklarının farkıdır. Böylece toplam tam olarak
`floor(eldeki * çarpan)` eder ve hiçbir satış eldeki lotu aşmaz. Kalan kesir (küsurat) nakde çevrilir:
`küsurat_lot * ex-date öncesi son kapanış / çarpan`. Kesirli defterde (ABD hissesi) küsurat oluşmaz.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from decimal import ROUND_FLOOR, Decimal
from typing import List, Optional, Sequence, Tuple

PRICE_PLACES = Decimal("0.0001")
CASH_PLACES = Decimal("0.01")


@dataclass(frozen=True)
class LedgerLot:
    """Bir defter işleminin bölünme hesabına giren alanları (ana portföy, model portföy veya varlık defteri)."""
    trade_id: int
    trade_date: date
    trade_time: Optional[time]
    is_buy: bool
    quantity: Decimal
    price: Decimal


@dataclass(frozen=True)
class LotAdjustment:
    trade_id: int
    pre_quantity: Decimal
    post_quantity: Decimal
    pre_price: Decimal
    post_price: Decimal


@dataclass(frozen=True)
class SplitAllocation:
    adjustments: Tuple[LotAdjustment, ...]
    held_before: Decimal
    held_after: Decimal
    fraction: Decimal  # nakde çevrilecek kesirli lot (tam lotlu defterde)

    def fraction_cash(self, last_close_before_ex: Optional[Decimal], multiplier: Decimal) -> Decimal:
        """Küsuratın ex-date teorik fiyatıyla nakit karşılığı; fiyat yoksa 0."""
        if self.fraction <= 0 or not last_close_before_ex or last_close_before_ex <= 0:
            return Decimal("0")
        return (self.fraction * last_close_before_ex / multiplier).quantize(CASH_PLACES)


def _scaled(quantity: Decimal, multiplier: Decimal, whole_lots: bool) -> Decimal:
    value = quantity * multiplier
    return value.to_integral_value(rounding=ROUND_FLOOR) if whole_lots else value


def _sort_key(lot: LedgerLot):
    return (lot.trade_date, lot.trade_time or time.min, lot.trade_id)


def allocate_split(
    lots: Sequence[LedgerLot],
    ex_date: date,
    multiplier: Decimal,
    whole_lots: bool = True,
) -> SplitAllocation:
    """Ex-date öncesi işlemler için yeni lot/fiyatları ve küsuratı hesaplar. Ters bölünmede (çarpan < 1) tam lotlu
    defterde bir işlem sıfır lota düşebilir; bu durumda ValueError (otomatik uygulanmaz, kullanıcı karar verir)."""
    if multiplier <= 0:
        raise ValueError("Split multiplier must be positive")
    held = Decimal("0")
    adjustments: List[LotAdjustment] = []
    for lot in sorted((l for l in lots if l.trade_date < ex_date), key=_sort_key):
        after = held + lot.quantity if lot.is_buy else held - lot.quantity
        post_quantity = abs(_scaled(after, multiplier, whole_lots) - _scaled(held, multiplier, whole_lots))
        if post_quantity <= 0:
            raise ValueError(f"Trade {lot.trade_id} would drop to zero lots after the split")
        post_price = (lot.price * lot.quantity / post_quantity).quantize(PRICE_PLACES)
        adjustments.append(LotAdjustment(lot.trade_id, lot.quantity, post_quantity, lot.price, post_price))
        held = after
    held_after = _scaled(held, multiplier, whole_lots)
    fraction = held * multiplier - held_after if whole_lots else Decimal("0")
    return SplitAllocation(tuple(adjustments), held, held_after, fraction)

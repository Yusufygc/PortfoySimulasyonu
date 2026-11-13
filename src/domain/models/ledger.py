"""Üç işlem defterinin (ana portföy, model portföyler, Portföyüm varlık defteri) ortak okuma modeli.

Defterler-arası özellikler (kurumsal aksiyonlar, fiyat kapsamı, takip edilen hisseler) üç tabloyu ayrı ayrı
sorgulamak yerine bu anlık görüntüyü kullanır: anahtar `(defter, model portföy id)`, değer işlem lotları.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from decimal import Decimal
from enum import Enum
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

from src.domain.split_math import LedgerLot


class LedgerKind(str, Enum):
    MAIN = "MAIN"     # ana portföy (trades)
    MODEL = "MODEL"   # model portföyler (model_portfolio_trades)
    ASSET = "ASSET"   # Portföyüm varlık defteri (asset_trades)


LedgerKey = Tuple[LedgerKind, Optional[int]]  # (defter, model portföy id)
KeyFilter = Callable[[LedgerKey], bool]


def _sort_key(lot: LedgerLot):
    return (lot.trade_date, lot.trade_time or time.min, lot.trade_id)


def _open_in(lots: Iterable[LedgerLot]) -> Dict[int, Decimal]:
    """Enstrüman başına eldeki miktar; eldekinden fazla satış atlanır (güvenli portföy kuralıyla aynı)."""
    held: Dict[int, Decimal] = {}
    for lot in sorted(lots, key=_sort_key):
        current = held.get(lot.instrument_id, Decimal("0"))
        if lot.is_buy:
            held[lot.instrument_id] = current + lot.quantity
        elif lot.quantity <= current:
            held[lot.instrument_id] = current - lot.quantity
    return held


@dataclass(frozen=True)
class LedgerSnapshot:
    lots: Dict[LedgerKey, List[LedgerLot]] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return not any(self.lots.values())

    def keys(self, include: Optional[KeyFilter] = None) -> List[LedgerKey]:
        return [k for k in self.lots if include is None or include(k)]

    def instruments(self, include: Optional[KeyFilter] = None) -> Set[int]:
        """İşlem görmüş (açık veya kapanmış) enstrümanlar."""
        return {lot.instrument_id for k in self.keys(include) for lot in self.lots[k] if lot.instrument_id is not None}

    def open_instruments(self, include: Optional[KeyFilter] = None) -> Set[int]:
        """En az bir defterde eldeki miktarı pozitif olan enstrümanlar (her defter ayrı hesaplanır)."""
        result: Set[int] = set()
        for k in self.keys(include):
            result.update(i for i, qty in _open_in(self.lots[k]).items() if qty > 0 and i is not None)
        return result

    def first_trade_dates(self, include: Optional[KeyFilter] = None) -> Dict[int, date]:
        first: Dict[int, date] = {}
        for k in self.keys(include):
            for lot in self.lots[k]:
                if lot.instrument_id is not None and (lot.instrument_id not in first or lot.trade_date < first[lot.instrument_id]):
                    first[lot.instrument_id] = lot.trade_date
        return first

"""Hisse bölünmesi / bedelsiz sermaye artırımı sinyali ve uzlaşı kararı (saf domain modelleri).

`multiplier` eski 1 lotun bölünme sonrası karşılığıdır: 11:1 bölünme ve %1000 bedelsiz 11, %50 bedelsiz 1,5;
ters bölünmede 1'den küçüktür. Bedelsiz oranıyla ilişki: `multiplier = 1 + ratio`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional, Tuple


class SplitSource(str, Enum):
    YAHOO = "YAHOO"
    KAP = "KAP"
    PRICE_BREAK = "PRICE_BREAK"


# Ex-date önceliği: resmi duyuru > fiyatın gerçekten değiştiği gün > veri sağlayıcı kaydı. Yahoo BIST bölünmelerini
# günler sonra tarihleyebilir (SDTTR 2026: Yahoo 27.08, fiyat kırılması 21.08).
SOURCE_PRIORITY: Tuple[SplitSource, ...] = (SplitSource.KAP, SplitSource.PRICE_BREAK, SplitSource.YAHOO)
# Çarpan önceliği: kesin oran veren kaynaklar önce; fiyat kırılması oranı yalnızca tahmindir (10,95 gibi).
MULTIPLIER_PRIORITY: Tuple[SplitSource, ...] = (SplitSource.KAP, SplitSource.YAHOO, SplitSource.PRICE_BREAK)


@dataclass(frozen=True)
class SplitSignal:
    ticker: str
    ex_date: date
    multiplier: Decimal
    source: SplitSource
    detail: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", (self.ticker or "").strip().upper().replace(".IS", ""))
        if not self.ticker:
            raise ValueError("Split signal ticker is required")
        if not isinstance(self.multiplier, Decimal):
            object.__setattr__(self, "multiplier", Decimal(str(self.multiplier)))
        if self.multiplier <= 0 or self.multiplier == 1:
            raise ValueError("Split multiplier must be positive and different from 1")
        if not isinstance(self.source, SplitSource):
            object.__setattr__(self, "source", SplitSource(self.source))


class SplitDecisionKind(str, Enum):
    AUTO = "AUTO"                      # en az iki bağımsız kaynak doğruladı: otomatik uygulanır
    CANDIDATE = "CANDIDATE"            # tek kaynak veya ters bölünme: kullanıcı onayı bekler
    ALREADY_APPLIED = "ALREADY_APPLIED"


@dataclass(frozen=True)
class SplitDecision:
    ticker: str
    ex_date: date
    multiplier: Decimal
    kind: SplitDecisionKind
    signals: Tuple[SplitSignal, ...] = field(default_factory=tuple)

    @property
    def sources(self) -> Tuple[SplitSource, ...]:
        return tuple(sorted({s.source for s in self.signals}, key=SOURCE_PRIORITY.index))

    @property
    def bedelsiz_ratio(self) -> Decimal:
        """Bedelsiz artırım oranı karşılığı (`multiplier - 1`); ters bölünmede negatiftir."""
        return self.multiplier - Decimal("1")

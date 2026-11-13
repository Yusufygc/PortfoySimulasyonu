from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Tuple

ZERO = Decimal("0")
HUNDRED = Decimal("100")


@dataclass(frozen=True)
class PositionSnapshot:
    """Tek hissenin bir portföydeki (ana ya da model) anlık değerlemesi; ekranların ortak rakam kaynağı.

    Fiyatı çözülemeyen pozisyon maliyetiyle değerlenir (`is_priced=False`); K/Z bu durumda 0'dır.
    `weight_pct`, portföyün toplam değerine (pozisyonlar + nakit) oranıdır.
    """

    stock_id: int
    ticker: str
    name: str
    quantity: int
    total_cost: Decimal
    price: Optional[Decimal] = None
    previous_close: Optional[Decimal] = None
    daily_change_pct: Optional[Decimal] = None
    weight_pct: Decimal = ZERO

    @property
    def is_priced(self) -> bool:
        return self.price is not None and self.price > 0

    @property
    def avg_cost(self) -> Decimal:
        return self.total_cost / Decimal(self.quantity) if self.quantity > 0 else ZERO

    @property
    def market_value(self) -> Decimal:
        return self.price * Decimal(self.quantity) if self.is_priced else self.total_cost

    @property
    def unrealized_pl(self) -> Decimal:
        return self.market_value - self.total_cost

    @property
    def unrealized_pl_pct(self) -> Optional[Decimal]:
        return self.unrealized_pl / self.total_cost * HUNDRED if self.total_cost > 0 else None

    @property
    def total_change_pct(self) -> Optional[Decimal]:
        """Fiyatın ortalama maliyete göre değişimi (K/Z yüzdesiyle aynı, ancak fiyat yoksa None)."""
        if not self.is_priced or self.avg_cost <= 0:
            return None
        return (self.price - self.avg_cost) / self.avg_cost * HUNDRED


@dataclass(frozen=True)
class PortfolioPositions:
    """Bir portföyün tüm pozisyonları ve toplamları (ana portföy ya da model portföy)."""

    positions: Tuple[PositionSnapshot, ...]
    cash: Decimal
    total_value: Decimal

    def find(self, stock_id: int) -> Optional[PositionSnapshot]:
        return next((p for p in self.positions if p.stock_id == stock_id), None)

# src/domain/models/unified_portfolio.py

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional, Tuple

from .asset import AssetClass

ZERO = Decimal("0")
HUNDRED = Decimal("100")


class AllocationClass(str, Enum):
    """Portföyüm dağılımındaki sınıflar: BIST hissesi, BIST dışı varlık sınıfları ve nakit."""

    BIST_STOCK = "BIST_STOCK"
    US_STOCK = "US_STOCK"
    CRYPTO = "CRYPTO"
    PRECIOUS_METAL = "PRECIOUS_METAL"
    CASH = "CASH"


def allocation_class_for(asset_class: AssetClass) -> AllocationClass:
    return AllocationClass(asset_class.value)


def daily_gain(value: Decimal, change_pct: Optional[Decimal]) -> Decimal:
    """Bugünkü değer ile önceki kapanışa göre değer arasındaki fark; değişim bilinmiyorsa 0."""
    if change_pct is None:
        return ZERO
    return value - value / (Decimal("1") + change_pct / HUNDRED)


@dataclass(frozen=True)
class HoldingValuation:
    """
    Tek bir pozisyonun TRY değerlemesi (BIST hissesi veya varlık defteri varlığı).

    - Değerlenemeyen pozisyon (fiyat veya kur yok) TRY maliyetiyle değerlenir; `is_priced=False` ile işaretlenir.
    - unrealized_pl_try, kur farkını da içerir (alım anı kuru ile güncel kur arasındaki fark).
    - daily_change_pct varlığın kendi para birimindeki günlük değişimdir; kur hareketi dahil değildir.
    """

    key: str
    symbol: str
    name: str
    allocation_class: AllocationClass
    quantity: Decimal
    native_currency: str
    cost_native: Decimal
    cost_try: Decimal
    value_try: Decimal
    price_native: Optional[Decimal] = None
    value_native: Optional[Decimal] = None
    daily_change_pct: Optional[Decimal] = None
    daily_gain_try: Decimal = ZERO
    weight_pct: Decimal = ZERO
    is_priced: bool = True
    ref_id: Optional[int] = None   # BIST için stock_id, varlık defteri için asset_id
    is_stale: bool = False         # fiyat veya kur eşikten eski (değer var ama güncel değil)

    @property
    def unrealized_pl_try(self) -> Decimal:
        return self.value_try - self.cost_try

    @property
    def unrealized_pl_pct(self) -> Optional[Decimal]:
        return self.unrealized_pl_try / self.cost_try * HUNDRED if self.cost_try > 0 else None


@dataclass(frozen=True)
class AllocationSlice:
    allocation_class: AllocationClass
    value_try: Decimal
    weight_pct: Decimal
    holdings_count: int


@dataclass(frozen=True)
class UnifiedSummary:
    """
    BIST portföyü, BIST nakdi ve varlık defterinin birleşik TRY özeti.

    Tüm tutarlar TRY'dir; `display_amount` değeri gösterim para birimine çevirir (USD anahtarı).
    `is_partial`, en az bir pozisyonun değerlenemediğini (maliyetle değerlendiğini) gösterir.
    """

    holdings: Tuple[HoldingValuation, ...]
    cash_try: Decimal
    total_value_try: Decimal
    total_cost_try: Decimal
    daily_gain_try: Decimal
    slices: Tuple[AllocationSlice, ...]
    unpriced_symbols: Tuple[str, ...] = ()
    stale_symbols: Tuple[str, ...] = ()  # fiyatı/kuru eşikten eski pozisyonlar
    display_currency: str = "TRY"
    display_rate: Decimal = Decimal("1")     # 1 TRY = ? gösterim para birimi
    display_unavailable: bool = False        # USD istendi ama kur yok: TRY gösterildi
    usd_try_rate: Optional[Decimal] = None

    @property
    def is_partial(self) -> bool:
        return bool(self.unpriced_symbols)

    @property
    def unrealized_pl_try(self) -> Decimal:
        """Açık pozisyonların gerçekleşmemiş K/Z'si (nakit hariç)."""
        return sum((h.unrealized_pl_try for h in self.holdings), ZERO)

    @property
    def unrealized_pl_pct(self) -> Optional[Decimal]:
        return self.unrealized_pl_try / self.total_cost_try * HUNDRED if self.total_cost_try > 0 else None

    @property
    def daily_change_pct(self) -> Optional[Decimal]:
        previous_value = self.total_value_try - self.daily_gain_try
        return self.daily_gain_try / previous_value * HUNDRED if previous_value > 0 else None

    def display_amount(self, amount_try: Decimal) -> Decimal:
        return amount_try * self.display_rate

    def holdings_of(self, allocation_class: AllocationClass) -> Tuple[HoldingValuation, ...]:
        return tuple(h for h in self.holdings if h.allocation_class == allocation_class)

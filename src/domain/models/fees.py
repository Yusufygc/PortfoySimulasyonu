from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal("0")
HUNDRED = Decimal("100")
FEE_PRECISION = Decimal("0.0001")

MAX_COMMISSION_PCT = Decimal("10")
MAX_BSMV_PCT = Decimal("100")


@dataclass(frozen=True)
class FeeRates:
    """İşlem ücreti oranları (yüzde). Varsayılan hepsi 0: ücret kesilmez.

    - bist_commission_pct: BIST hisse işlemi komisyonu (işlem tutarı üzerinden)
    - asset_commission_pct: BIST dışı varlık (altın, kripto, ABD hissesi) komisyonu
    - bsmv_pct: BSMV, komisyon tutarı üzerinden alınır (ör. %5)
    """

    bist_commission_pct: Decimal = ZERO
    asset_commission_pct: Decimal = ZERO
    bsmv_pct: Decimal = ZERO

    def __post_init__(self) -> None:
        for name in ("bist_commission_pct", "asset_commission_pct", "bsmv_pct"):
            value = getattr(self, name)
            object.__setattr__(self, name, value if isinstance(value, Decimal) else Decimal(str(value)))
        for name in ("bist_commission_pct", "asset_commission_pct"):
            if not ZERO <= getattr(self, name) <= MAX_COMMISSION_PCT:
                raise ValueError(f"Komisyon oranı 0 ile {MAX_COMMISSION_PCT} arasında olmalı.")
        if not ZERO <= self.bsmv_pct <= MAX_BSMV_PCT:
            raise ValueError(f"BSMV oranı 0 ile {MAX_BSMV_PCT} arasında olmalı.")


def calculate_fee(gross_amount: Decimal, commission_pct: Decimal, bsmv_pct: Decimal) -> Decimal:
    """Toplam ücret = komisyon + BSMV; komisyon = tutar x oran, BSMV = komisyon x BSMV oranı. 4 haneye yuvarlanır."""
    commission = gross_amount * commission_pct / HUNDRED
    total = commission + commission * bsmv_pct / HUNDRED
    return total.quantize(FEE_PRECISION, rounding=ROUND_HALF_UP)

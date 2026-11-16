from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal("0")
HUNDRED = Decimal("100")
FEE_PRECISION = Decimal("0.0001")

MAX_COMMISSION_PCT = Decimal("10")
MAX_BSMV_PCT = Decimal("100")
MAX_FIXED_FEE = Decimal("100000")

FEE_MODE_PCT = "PCT"
FEE_MODE_FIXED = "FIXED"
VALID_FEE_MODES = (FEE_MODE_PCT, FEE_MODE_FIXED)


def _validate_fee_value(value: Decimal, mode: str, max_pct: Decimal, label: str) -> None:
    if mode == FEE_MODE_FIXED:
        if not ZERO <= value <= MAX_FIXED_FEE:
            raise ValueError(f"Sabit ücret 0 ile {MAX_FIXED_FEE} arasında olmalı.")
    elif not ZERO <= value <= max_pct:
        raise ValueError(f"{label} 0 ile {max_pct} arasında olmalı.")


@dataclass(frozen=True)
class FeeRates:
    """İşlem ücreti ayarları (yüzdesel oran veya sabit tutar). Varsayılan hepsi 0 (%): ücret kesilmez.

    - bist_commission_pct / bist_mode: BIST hisse işlemi komisyonu (% veya sabit tutar)
    - asset_commission_pct / asset_mode: BIST dışı varlık (altın, kripto, ABD hissesi) komisyonu
    - bsmv_pct / bsmv_mode: BSMV, komisyon tutarı üzerinden yüzde (ör. %5) veya sabit tutar
    """

    bist_commission_pct: Decimal = ZERO
    asset_commission_pct: Decimal = ZERO
    bsmv_pct: Decimal = ZERO
    bist_mode: str = FEE_MODE_PCT
    asset_mode: str = FEE_MODE_PCT
    bsmv_mode: str = FEE_MODE_PCT

    def __post_init__(self) -> None:
        for name in ("bist_commission_pct", "asset_commission_pct", "bsmv_pct"):
            value = getattr(self, name)
            object.__setattr__(self, name, value if isinstance(value, Decimal) else Decimal(str(value)))
        for mode_name in ("bist_mode", "asset_mode", "bsmv_mode"):
            mode_val = str(getattr(self, mode_name)).strip().upper()
            if mode_val not in VALID_FEE_MODES:
                raise ValueError("Geçersiz ücret türü.")
            object.__setattr__(self, mode_name, mode_val)
        _validate_fee_value(self.bist_commission_pct, self.bist_mode, MAX_COMMISSION_PCT, "Komisyon oranı")
        _validate_fee_value(self.asset_commission_pct, self.asset_mode, MAX_COMMISSION_PCT, "Komisyon oranı")
        _validate_fee_value(self.bsmv_pct, self.bsmv_mode, MAX_BSMV_PCT, "BSMV oranı")


def calculate_fee(
    gross_amount: Decimal,
    commission_pct: Decimal,
    bsmv_pct: Decimal,
    commission_mode: str = FEE_MODE_PCT,
    bsmv_mode: str = FEE_MODE_PCT,
) -> Decimal:
    """Toplam ücret = komisyon + BSMV; her biri yüzde veya sabit tutar olabilir. 4 haneye yuvarlanır."""
    if gross_amount <= ZERO:
        return ZERO.quantize(FEE_PRECISION, rounding=ROUND_HALF_UP)
    if commission_mode == FEE_MODE_FIXED:
        commission = commission_pct
    else:
        commission = gross_amount * commission_pct / HUNDRED
    if bsmv_mode == FEE_MODE_FIXED:
        bsmv = bsmv_pct
    else:
        bsmv = commission * bsmv_pct / HUNDRED
    total = commission + bsmv
    return total.quantize(FEE_PRECISION, rounding=ROUND_HALF_UP)

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal
from enum import Enum
from typing import Optional


class FxSide(str, Enum):
    """TL <-> USD döviz işlemi yönü (ortak nakit havuzunda yalnızca bu çift desteklenir)."""

    BUY_USD = "BUY_USD"    # TL verip USD alır
    SELL_USD = "SELL_USD"  # USD verip TL alır


def _to_decimal(value, field_name: str) -> Decimal:
    if isinstance(value, float):
        raise TypeError(f"{field_name} must not be a float; use Decimal or str")
    return value if isinstance(value, Decimal) else Decimal(str(value))


@dataclass(frozen=True)
class FxConversion:
    """
    Nakit havuzunda TL ile USD arasında döviz çevirme (iç transfer; dış sermaye akışı değildir).

    - usd_amount: işleme konu USD miktarı
    - rate: 1 USD = X TRY (işlem kuru)
    - fee_try: işlem ücreti (TL); alımda TL çıkışına eklenir, satışta TL girişinden düşer
    """

    id: Optional[int]
    conversion_date: date
    conversion_time: Optional[time]
    side: FxSide
    usd_amount: Decimal
    rate: Decimal
    fee_try: Decimal = Decimal("0")
    note: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.side, FxSide):
            try:
                object.__setattr__(self, "side", FxSide(self.side))
            except ValueError as exc:
                raise ValueError(f"Unknown FX side: {self.side}") from exc
        for name in ("usd_amount", "rate", "fee_try"):
            object.__setattr__(self, name, _to_decimal(getattr(self, name), name))
        if self.usd_amount <= 0:
            raise ValueError("USD amount must be positive")
        if self.rate <= 0:
            raise ValueError("FX rate must be positive")
        if self.fee_try < 0:
            raise ValueError("Fee cannot be negative")

    @property
    def try_amount(self) -> Decimal:
        """Ücretsiz TL karşılığı (USD x kur)."""
        return self.usd_amount * self.rate

    @property
    def try_effect(self) -> Decimal:
        """TL nakide etkisi: alımda -(tutar + ücret), satışta +(tutar - ücret)."""
        if self.side == FxSide.BUY_USD:
            return -(self.try_amount + self.fee_try)
        return self.try_amount - self.fee_try

    @property
    def usd_effect(self) -> Decimal:
        """USD nakide etkisi: alımda +USD, satışta -USD."""
        return self.usd_amount if self.side == FxSide.BUY_USD else -self.usd_amount

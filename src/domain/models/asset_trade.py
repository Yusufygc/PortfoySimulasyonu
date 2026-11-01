# src/domain/models/asset_trade.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal
from typing import Optional

from .trade import TradeSide


def _to_decimal(value, field_name: str) -> Decimal:
    if isinstance(value, float):
        raise TypeError(f"{field_name} must not be a float; use Decimal or str")
    return value if isinstance(value, Decimal) else Decimal(str(value))


@dataclass(frozen=True)
class AssetTrade:
    """
    Varlık defterindeki tek bir alım/satım işlemi (kesirli miktar destekler).

    - quantity / price: varlığın kendi birimi ve para biriminde
    - fx_rate_to_try: işlem anındaki 1 birim `quote_currency` = X TRY (TRY varlıklarda 1)
    """

    id: Optional[int]
    asset_id: int
    trade_date: date
    trade_time: Optional[time]
    side: TradeSide
    quantity: Decimal
    price: Decimal
    fx_rate_to_try: Decimal = Decimal("1")
    note: Optional[str] = None
    fee: Decimal = Decimal("0")   # komisyon + BSMV, işlemin para biriminde mutlak tutar

    def __post_init__(self) -> None:
        if not isinstance(self.side, TradeSide):
            try:
                object.__setattr__(self, "side", TradeSide(self.side))
            except ValueError as exc:
                raise ValueError(f"Unknown trade side: {self.side}") from exc

        object.__setattr__(self, "quantity", _to_decimal(self.quantity, "quantity"))
        object.__setattr__(self, "price", _to_decimal(self.price, "price"))
        object.__setattr__(self, "fx_rate_to_try", _to_decimal(self.fx_rate_to_try, "fx_rate_to_try"))
        object.__setattr__(self, "fee", _to_decimal(self.fee, "fee"))

        if self.asset_id <= 0:
            raise ValueError("Asset id must be positive")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.price <= 0:
            raise ValueError("Price must be positive")
        if self.fx_rate_to_try <= 0:
            raise ValueError("FX rate must be positive")
        if self.fee < 0:
            raise ValueError("Fee cannot be negative")

    @property
    def total_amount(self) -> Decimal:
        """İşlem tutarı (varlığın para biriminde)."""
        return self.price * self.quantity

    @property
    def cash_amount(self) -> Decimal:
        """Nakit etkisinin büyüklüğü (işlem para biriminde): alımda tutar + ücret, satışta tutar - ücret."""
        return self.total_amount + self.fee if self.side == TradeSide.BUY else self.total_amount - self.fee

    @property
    def total_amount_try(self) -> Decimal:
        """İşlem tutarı (işlem anındaki kurla TRY)."""
        return self.total_amount * self.fx_rate_to_try

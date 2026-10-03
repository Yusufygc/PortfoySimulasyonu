from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Optional


class CashMovementType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"
    DIVIDEND = "DIVIDEND"

    @property
    def adds_cash(self) -> bool:
        """Nakit bakiyesini artırır (yatırma ve temettü)."""
        return self in (CashMovementType.DEPOSIT, CashMovementType.DIVIDEND)

    @property
    def is_external_flow(self) -> bool:
        """Portföye dışarıdan giren/çıkan sermayedir; temettü portföyün getirisidir, dış akış sayılmaz."""
        return self in (CashMovementType.DEPOSIT, CashMovementType.WITHDRAW)


@dataclass(frozen=True)
class CashMovement:
    id: Optional[int]
    movement_date: date
    movement_time: Optional[time]
    type: CashMovementType
    amount: Decimal
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    stock_id: Optional[int] = None  # yalnızca temettü hareketlerinde dolu

    def __post_init__(self) -> None:
        if not isinstance(self.type, CashMovementType):
            try:
                object.__setattr__(self, "type", CashMovementType(self.type))
            except ValueError as exc:
                raise ValueError(f"Unknown cash movement type: {self.type}") from exc

        self._validate_amount(self.amount)
        if self.type == CashMovementType.DIVIDEND and self.stock_id is None:
            raise ValueError("Temettü hareketi bir hisseye bağlı olmalıdır.")

    @classmethod
    def create_deposit(
        cls,
        amount: Decimal,
        movement_date: date,
        movement_time: Optional[time] = None,
        notes: Optional[str] = None,
    ) -> "CashMovement":
        cls._validate_amount(amount)
        return cls(
            id=None,
            movement_date=movement_date,
            movement_time=movement_time,
            type=CashMovementType.DEPOSIT,
            amount=amount,
            notes=notes,
        )

    @classmethod
    def create_withdraw(
        cls,
        amount: Decimal,
        movement_date: date,
        movement_time: Optional[time] = None,
        notes: Optional[str] = None,
    ) -> "CashMovement":
        cls._validate_amount(amount)
        return cls(
            id=None,
            movement_date=movement_date,
            movement_time=movement_time,
            type=CashMovementType.WITHDRAW,
            amount=amount,
            notes=notes,
        )

    @classmethod
    def create_dividend(
        cls,
        stock_id: int,
        amount: Decimal,
        movement_date: date,
        movement_time: Optional[time] = None,
        notes: Optional[str] = None,
    ) -> "CashMovement":
        cls._validate_amount(amount)
        return cls(
            id=None,
            movement_date=movement_date,
            movement_time=movement_time,
            type=CashMovementType.DIVIDEND,
            amount=amount,
            notes=notes,
            stock_id=stock_id,
        )

    @staticmethod
    def _validate_amount(amount: Decimal) -> None:
        if amount <= 0:
            raise ValueError("Nakit hareketi tutarı pozitif olmalıdır.")

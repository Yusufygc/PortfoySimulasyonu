from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Optional


class CashMovementType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"


@dataclass(frozen=True)
class CashMovement:
    id: Optional[int]
    movement_date: date
    movement_time: Optional[time]
    type: CashMovementType
    amount: Decimal
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

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

    @staticmethod
    def _validate_amount(amount: Decimal) -> None:
        if amount <= 0:
            raise ValueError("Nakit hareketi tutarı pozitif olmalıdır.")

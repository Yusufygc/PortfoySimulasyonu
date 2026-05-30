from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from src.domain.models.cash_movement import CashMovement


class CashMovementService:
    def __init__(self, cash_movement_repo, portfolio_service=None) -> None:
        self._cash_movement_repo = cash_movement_repo
        self._portfolio_service = portfolio_service

    def add_deposit(
        self,
        amount: Decimal,
        movement_date: Optional[date] = None,
        movement_time: Optional[time] = None,
        notes: Optional[str] = None,
    ) -> CashMovement:
        movement = CashMovement.create_deposit(
            amount=amount,
            movement_date=movement_date or date.today(),
            movement_time=movement_time or datetime.now().time().replace(microsecond=0),
            notes=notes,
        )
        return self._cash_movement_repo.insert_movement(movement)

    def add_withdraw(
        self,
        amount: Decimal,
        movement_date: Optional[date] = None,
        movement_time: Optional[time] = None,
        notes: Optional[str] = None,
    ) -> CashMovement:
        if self._portfolio_service is not None:
            balance = self._portfolio_service.get_cash_balance()
            if amount > balance:
                raise ValueError(f"Yetersiz nakit. Çekilecek: {amount:.2f} TL, Mevcut: {balance:.2f} TL")
        movement = CashMovement.create_withdraw(
            amount=amount,
            movement_date=movement_date or date.today(),
            movement_time=movement_time or datetime.now().time().replace(microsecond=0),
            notes=notes,
        )
        return self._cash_movement_repo.insert_movement(movement)

    def get_cash_balance(self, as_of: date | tuple[date, time | None] | None = None) -> Decimal:
        if self._portfolio_service is not None:
            return self._portfolio_service.get_cash_balance(as_of=as_of)
        movements = self.get_movements(as_of=as_of)
        return self._movement_balance(movements)

    def get_movements(self, as_of: date | tuple[date, time | None] | None = None):
        if as_of is None:
            return self._cash_movement_repo.get_all_movements()
        if isinstance(as_of, tuple):
            return self._cash_movement_repo.get_movements_until(as_of[0], as_of[1])
        return self._cash_movement_repo.get_movements_until(as_of)

    @staticmethod
    def _movement_balance(movements) -> Decimal:
        balance = Decimal("0")
        for movement in movements:
            if movement.type.value == "DEPOSIT":
                balance += movement.amount
            else:
                balance -= movement.amount
                if balance < 0:
                    balance = Decimal("0")
        return balance

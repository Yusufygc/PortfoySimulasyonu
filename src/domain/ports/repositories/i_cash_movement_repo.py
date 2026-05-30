from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, time
from typing import Iterable, List, Optional

from src.domain.models.cash_movement import CashMovement


class ICashMovementRepository(ABC):
    @abstractmethod
    def get_all_movements(self) -> List[CashMovement]:
        raise NotImplementedError

    @abstractmethod
    def get_movements_until(
        self,
        movement_date: date,
        movement_time: Optional[time] = None,
    ) -> List[CashMovement]:
        raise NotImplementedError

    @abstractmethod
    def insert_movement(self, movement: CashMovement) -> CashMovement:
        raise NotImplementedError

    @abstractmethod
    def insert_movements_bulk(self, movements: Iterable[CashMovement]) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_all_movements(self) -> None:
        raise NotImplementedError

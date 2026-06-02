from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional


VALID_BUDGET_ITEM_TYPES = {"income", "expense"}


def _to_decimal(value: Decimal | float | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass
class BudgetItem:
    """Single income or expense item in a monthly budget."""

    id: Optional[int]
    budget_id: Optional[int]
    item_type: str
    name: str
    amount: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.item_type not in VALID_BUDGET_ITEM_TYPES:
            raise ValueError(f"Unknown budget item type: {self.item_type}")
        self.amount = _to_decimal(self.amount)
        if self.amount < 0:
            raise ValueError("Budget item amount cannot be negative")


@dataclass
class Budget:
    """Domain model for a monthly budget and its dynamic items."""

    id: Optional[int]
    month: str
    savings_target: Decimal = Decimal("0")
    items: List[BudgetItem] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        self.savings_target = _to_decimal(self.savings_target)
        if self.savings_target < 0:
            raise ValueError("Savings target cannot be negative")

    @property
    def total_income(self) -> Decimal:
        """Total income."""
        return sum((i.amount for i in self.items if i.item_type == "income"), Decimal("0"))

    @property
    def total_expense(self) -> Decimal:
        """Total expense."""
        return sum((i.amount for i in self.items if i.item_type == "expense"), Decimal("0"))

    @property
    def net_savings_potential(self) -> Decimal:
        """Net savings potential = income - expense."""
        return self.total_income - self.total_expense

    @property
    def status_message(self) -> str:
        """Automatic budget status message."""
        net = self.net_savings_potential
        if net < 0:
            return "DIKKAT: Geliriniz giderlerinizi karsilamiyor. Acik veriyorsunuz."
        if net < self.savings_target:
            return "Hedeflenen tasarrufun altindasiniz. Harcamalari kismaniz onerilir."
        return "Harika! Hedeflenen tasarrufu gerceklestirebilirsiniz."

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


class GoalPriority:
    """Financial goal priority constants."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class GoalStatus:
    """Financial goal status constants."""

    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


def _to_decimal(value: Decimal | float | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass
class FinancialGoal:
    """
    Domain model for a financial savings goal.

    Represents the financial_goals table in domain terms.
    """

    id: Optional[int]
    name: str
    target_amount: Decimal
    current_amount: Decimal = Decimal("0")
    deadline: Optional[date] = None
    priority: str = GoalPriority.MEDIUM
    status: str = GoalStatus.ACTIVE

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        self.target_amount = _to_decimal(self.target_amount)
        self.current_amount = _to_decimal(self.current_amount)

        if self.target_amount < 0:
            raise ValueError("Target amount cannot be negative")
        if self.current_amount < 0:
            raise ValueError("Current amount cannot be negative")

    @property
    def remaining_amount(self) -> Decimal:
        """Amount still needed to complete the goal."""
        return max(self.target_amount - self.current_amount, Decimal("0"))

    @property
    def progress_ratio(self) -> float:
        """Progress ratio between 0.0 and 1.0."""
        if self.target_amount <= 0:
            return 0.0
        return min(float(self.current_amount / self.target_amount), 1.0)

    @property
    def is_completed(self) -> bool:
        """Whether the goal has reached its target amount."""
        return self.current_amount >= self.target_amount

    def months_remaining(self, today: Optional[date] = None) -> int:
        """Months remaining until the deadline. Returns 0 for past deadlines."""
        if self.deadline is None:
            return 0

        today = today or date.today()
        if self.deadline <= today:
            return 0

        delta_years = self.deadline.year - today.year
        delta_months = self.deadline.month - today.month
        return max(delta_years * 12 + delta_months, 0)

    def required_monthly_contribution(self, today: Optional[date] = None) -> Decimal:
        """Monthly contribution needed to reach the goal."""
        months = self.months_remaining(today=today)
        if months <= 0:
            return self.remaining_amount
        return self.remaining_amount / Decimal(months)

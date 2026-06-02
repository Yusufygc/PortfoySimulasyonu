from datetime import date
from decimal import Decimal

from src.domain.models.financial_goal import FinancialGoal


def test_progress_and_remaining_amount_are_capped():
    goal = FinancialGoal(
        id=None,
        name="Emergency fund",
        target_amount=1000.0,
        current_amount=1200.0,
    )

    assert goal.remaining_amount == Decimal("0")
    assert goal.progress_ratio == 1.0
    assert goal.is_completed is True


def test_months_remaining_uses_supplied_today_for_deterministic_calculation():
    goal = FinancialGoal(
        id=None,
        name="Car",
        target_amount=12000.0,
        current_amount=0.0,
        deadline=date(2026, 7, 15),
    )

    assert goal.months_remaining(today=date(2026, 1, 1)) == 6


def test_months_remaining_returns_zero_without_deadline_or_for_past_deadline():
    without_deadline = FinancialGoal(
        id=None,
        name="Open ended",
        target_amount=1000.0,
    )
    past_deadline = FinancialGoal(
        id=None,
        name="Past",
        target_amount=1000.0,
        deadline=date(2026, 1, 1),
    )

    assert without_deadline.months_remaining(today=date(2026, 1, 1)) == 0
    assert past_deadline.months_remaining(today=date(2026, 1, 2)) == 0


def test_required_monthly_contribution_uses_supplied_today():
    goal = FinancialGoal(
        id=None,
        name="House",
        target_amount=12000.0,
        current_amount=6000.0,
        deadline=date(2026, 7, 1),
    )

    assert goal.required_monthly_contribution(today=date(2026, 1, 1)) == Decimal("1000.0")


def test_required_monthly_contribution_returns_remaining_amount_when_no_months_left():
    goal = FinancialGoal(
        id=None,
        name="Immediate",
        target_amount=12000.0,
        current_amount=6000.0,
        deadline=date(2026, 1, 1),
    )

    assert goal.required_monthly_contribution(today=date(2026, 1, 1)) == Decimal("6000.0")


def test_amounts_are_normalized_to_decimal_and_negative_amounts_are_rejected():
    goal = FinancialGoal(
        id=None,
        name="Decimal goal",
        target_amount=1000.10,
        current_amount="250.05",
    )

    assert goal.target_amount == Decimal("1000.1")
    assert goal.current_amount == Decimal("250.05")
    assert goal.remaining_amount == Decimal("750.05")

    import pytest

    with pytest.raises(ValueError, match="Target amount"):
        FinancialGoal(id=None, name="Invalid", target_amount=-1)

    with pytest.raises(ValueError, match="Current amount"):
        FinancialGoal(id=None, name="Invalid", target_amount=1, current_amount=-1)

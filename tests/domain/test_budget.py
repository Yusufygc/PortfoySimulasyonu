from decimal import Decimal

import pytest

from src.domain.models.budget import Budget, BudgetItem


def test_budget_amounts_are_normalized_to_decimal():
    budget = Budget(
        id=None,
        month="2026-01",
        savings_target=1000.10,
        items=[
            BudgetItem(id=None, budget_id=None, item_type="income", name="Salary", amount=3000.20),
            BudgetItem(id=None, budget_id=None, item_type="expense", name="Rent", amount="1000.05"),
        ],
    )

    assert budget.savings_target == Decimal("1000.1")
    assert budget.total_income == Decimal("3000.2")
    assert budget.total_expense == Decimal("1000.05")
    assert budget.net_savings_potential == Decimal("2000.15")


def test_budget_rejects_invalid_item_type_and_negative_amounts():
    with pytest.raises(ValueError, match="Unknown budget item type"):
        BudgetItem(id=None, budget_id=None, item_type="other", name="Invalid", amount=1)

    with pytest.raises(ValueError, match="cannot be negative"):
        BudgetItem(id=None, budget_id=None, item_type="income", name="Invalid", amount=-1)

    with pytest.raises(ValueError, match="Savings target"):
        Budget(id=None, month="2026-01", savings_target=-1)


def test_budget_status_message_uses_decimal_comparisons():
    under_target = Budget(
        id=None,
        month="2026-01",
        savings_target=Decimal("1000.00"),
        items=[
            BudgetItem(id=None, budget_id=None, item_type="income", name="Salary", amount=Decimal("2000.00")),
            BudgetItem(id=None, budget_id=None, item_type="expense", name="Rent", amount=Decimal("1500.00")),
        ],
    )
    over_target = Budget(
        id=None,
        month="2026-02",
        savings_target=Decimal("1000.00"),
        items=[
            BudgetItem(id=None, budget_id=None, item_type="income", name="Salary", amount=Decimal("3000.00")),
            BudgetItem(id=None, budget_id=None, item_type="expense", name="Rent", amount=Decimal("1000.00")),
        ],
    )

    assert "altindasiniz" in under_target.status_message
    assert "Harika" in over_target.status_message

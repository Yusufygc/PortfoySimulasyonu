from decimal import Decimal

from src.application.services.planning.planning_service import PlanningService
from src.domain.models.budget import Budget, BudgetItem
from src.domain.models.financial_goal import FinancialGoal


class FakePlanningRepo:
    def __init__(self, budget, goals=None):
        self._budget = budget
        self._goals = goals or []

    def get_budget_by_month(self, month):
        return self._budget

    def get_all_budgets(self):
        return [self._budget]

    def get_active_goals(self):
        return self._goals


def test_get_monthly_analysis_preserves_float_output_contract():
    budget = Budget(
        id=1,
        month="2026-01",
        savings_target=Decimal("1000.00"),
        items=[
            BudgetItem(id=1, budget_id=1, item_type="income", name="Salary", amount=Decimal("3000.00")),
            BudgetItem(id=2, budget_id=1, item_type="expense", name="Rent", amount=Decimal("1250.50")),
        ],
    )
    service = PlanningService(FakePlanningRepo(budget))

    result = service.get_monthly_analysis("2026-01")

    assert result["total_income"] == 3000.0
    assert result["total_expense"] == 1250.5
    assert result["net_potential"] == 1749.5
    assert result["target"] == 1000.0
    assert result["breakdown"] == {"Salary": 3000.0, "Rent": 1250.5}


def test_analyze_feasibility_preserves_float_output_contract_for_goal_amounts():
    budget = Budget(
        id=1,
        month="2026-01",
        savings_target=Decimal("1000.00"),
        items=[
            BudgetItem(id=1, budget_id=1, item_type="income", name="Salary", amount=Decimal("3000.00")),
            BudgetItem(id=2, budget_id=1, item_type="expense", name="Rent", amount=Decimal("1000.00")),
        ],
    )
    goal = FinancialGoal(
        id=10,
        name="House",
        target_amount=Decimal("12000.00"),
        current_amount=Decimal("6000.00"),
    )
    service = PlanningService(FakePlanningRepo(budget, goals=[goal]))

    result = service.analyze_feasibility()

    assert result["monthly_power"] == 2000.0
    assert result["total_monthly_need"] == 6000.0
    assert result["details"][0]["target"] == 12000.0
    assert result["details"][0]["saved"] == 6000.0
    assert result["details"][0]["remaining"] == 6000.0
    assert result["details"][0]["required_monthly"] == 6000.0

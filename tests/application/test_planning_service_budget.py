from decimal import Decimal

from src.application.services.planning.planning_service import PlanningService
from src.domain.models.budget import Budget, BudgetItem, BudgetPinnedItem
from src.domain.models.financial_goal import FinancialGoal


class FakePlanningRepo:
    def __init__(self, budget=None, goals=None, pinned_items=None):
        self._budget = budget
        self._goals = goals or []
        self._pinned_items = pinned_items or []
        self.deleted_pinned_item = None

    def get_budget_by_month(self, month):
        return self._budget

    def get_all_budgets(self):
        return [self._budget] if self._budget else []

    def get_active_goals(self):
        return self._goals

    def get_pinned_budget_items(self):
        return self._pinned_items

    def upsert_pinned_budget_item(self, item):
        for index, existing in enumerate(self._pinned_items):
            if existing.item_type == item.item_type and existing.name == item.name:
                updated = BudgetPinnedItem(
                    id=existing.id,
                    item_type=item.item_type,
                    name=item.name,
                    default_amount=item.default_amount,
                )
                self._pinned_items[index] = updated
                return updated
        saved = BudgetPinnedItem(
            id=len(self._pinned_items) + 1,
            item_type=item.item_type,
            name=item.name,
            default_amount=item.default_amount,
        )
        self._pinned_items.append(saved)
        return saved

    def delete_pinned_budget_item(self, item_type, name):
        self.deleted_pinned_item = (item_type, name)
        self._pinned_items = [
            item
            for item in self._pinned_items
            if not (item.item_type == item_type and item.name == name)
        ]


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


def test_pin_budget_item_upserts_existing_title_without_duplicate():
    repo = FakePlanningRepo(
        pinned_items=[
            BudgetPinnedItem(id=1, item_type="expense", name="Rent", default_amount=Decimal("1000.00")),
        ],
    )
    service = PlanningService(repo)

    saved = service.pin_budget_item("expense", " Rent ", 1250.50)

    assert saved.id == 1
    assert saved.name == "Rent"
    assert saved.default_amount == Decimal("1250.5")
    assert len(repo.get_pinned_budget_items()) == 1


def test_unpin_budget_item_deletes_by_type_and_name():
    repo = FakePlanningRepo(
        pinned_items=[
            BudgetPinnedItem(id=1, item_type="income", name="Salary", default_amount=Decimal("3000.00")),
        ],
    )
    service = PlanningService(repo)

    service.unpin_budget_item("income", " Salary ")

    assert repo.deleted_pinned_item == ("income", "Salary")
    assert repo.get_pinned_budget_items() == []


def test_budget_draft_from_pinned_items_uses_default_amounts():
    service = PlanningService(
        FakePlanningRepo(
            pinned_items=[
                BudgetPinnedItem(id=1, item_type="income", name="Salary", default_amount=Decimal("3000.00")),
                BudgetPinnedItem(id=2, item_type="expense", name="Rent", default_amount=Decimal("1250.50")),
            ],
        )
    )

    draft = service.get_budget_draft_from_pinned_items("2026-02")

    assert draft.id is None
    assert draft.month == "2026-02"
    assert draft.savings_target == Decimal("0")
    assert [(item.item_type, item.name, item.amount) for item in draft.items] == [
        ("income", "Salary", Decimal("3000.00")),
        ("expense", "Rent", Decimal("1250.50")),
    ]

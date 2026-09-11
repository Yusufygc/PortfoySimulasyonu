"""CashflowController — d6 CashflowView (Bütçe + Hedefler + Nakit Hareketleri) köprüsü testleri."""
from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.domain.models.budget import Budget, BudgetItem, BudgetPinnedItem
from src.domain.models.cash_movement import CashMovement
from src.domain.models.financial_goal import FinancialGoal
from src.ui_qml.controllers.cashflow_controller import CashflowController


def _make_container(
    budget=None,
    pinned_items=None,
    goals=None,
    movements=None,
    cash_balance=Decimal("0"),
):
    container = MagicMock()
    planning = container.planning_service
    planning.get_budget_for_month.return_value = budget
    planning.get_budget_draft_from_pinned_items.return_value = Budget(
        id=None, month="2026-09", savings_target=Decimal("0"), items=[],
    )
    planning.get_pinned_budget_items.return_value = pinned_items or []
    planning.get_all_goals.return_value = goals or []

    cash = container.cash_movement_service
    cash.get_movements.return_value = movements or []
    cash.get_cash_balance.return_value = cash_balance
    return container


class TestBudgetInitialLoad:
    def test_no_saved_budget_falls_back_to_pinned_draft(self, qapp):
        controller = CashflowController(_make_container())
        assert controller.budgetItemTypes == []
        assert controller.totalIncome == 0.0

    def test_saved_budget_items_loaded(self, qapp):
        budget = Budget(
            id=1, month=date.today().strftime("%Y-%m"), savings_target=Decimal("2000"),
            items=[
                BudgetItem(id=None, budget_id=None, item_type="income", name="Maaş", amount=Decimal("30000")),
                BudgetItem(id=None, budget_id=None, item_type="expense", name="Kira", amount=Decimal("10000")),
            ],
        )
        controller = CashflowController(_make_container(budget=budget))

        assert controller.budgetItemTypes == ["income", "expense"]
        assert controller.budgetItemNames == ["Maaş", "Kira"]
        assert controller.totalIncome == pytest.approx(30000.0)
        assert controller.totalExpense == pytest.approx(10000.0)
        assert controller.netSavingsPotential == pytest.approx(20000.0)
        assert controller.savingsTarget == pytest.approx(2000.0)

    def test_pinned_items_loaded(self, qapp):
        pinned = [BudgetPinnedItem(id=1, item_type="expense", name="Kira", default_amount=Decimal("10000"))]
        controller = CashflowController(_make_container(pinned_items=pinned))
        assert controller.pinnedItemNames == ["Kira"]
        assert controller.pinnedItemAmounts == [10000.0]


class TestBudgetEditing:
    def test_add_budget_item_updates_totals(self, qapp):
        controller = CashflowController(_make_container())
        controller.addBudgetItem("income", "Maaş", 25000.0)
        assert controller.budgetItemNames == ["Maaş"]
        assert controller.totalIncome == pytest.approx(25000.0)

    def test_add_item_rejects_invalid_type_or_amount(self, qapp):
        controller = CashflowController(_make_container())
        controller.addBudgetItem("gecersiz", "X", 100.0)
        controller.addBudgetItem("income", "Y", -5.0)
        controller.addBudgetItem("income", "  ", 100.0)
        assert controller.budgetItemNames == []

    def test_remove_budget_item(self, qapp):
        controller = CashflowController(_make_container())
        controller.addBudgetItem("income", "Maaş", 25000.0)
        controller.addBudgetItem("expense", "Kira", 8000.0)

        controller.removeBudgetItem(0)

        assert controller.budgetItemNames == ["Kira"]
        assert controller.totalIncome == 0.0

    def test_status_message_reflects_deficit(self, qapp):
        controller = CashflowController(_make_container())
        controller.addBudgetItem("expense", "Kira", 8000.0)
        assert "carsilamiyor" in controller.budgetStatusMessage.lower() or "acik" in controller.budgetStatusMessage.lower()


class TestBudgetSave:
    def test_save_budget_delegates_to_planning_service(self, qapp):
        container = _make_container()
        controller = CashflowController(container)
        controller.addBudgetItem("income", "Maaş", 25000.0)

        controller.saveBudget()

        container.planning_service.save_budget.assert_called_once()
        saved_budget = container.planning_service.save_budget.call_args.args[0]
        assert saved_budget.total_income == Decimal("25000")
        assert controller.budgetError == ""

    def test_save_budget_error_is_captured(self, qapp):
        container = _make_container()
        container.planning_service.save_budget.side_effect = ValueError("Ay formatı hatalı")
        controller = CashflowController(container)

        controller.saveBudget()

        assert controller.budgetError == "Ay formatı hatalı"


class TestBudgetPinning:
    def test_toggle_pin_true_calls_pin_budget_item(self, qapp):
        container = _make_container()
        controller = CashflowController(container)
        controller.togglePinBudgetItem("expense", "Kira", 8000.0, True)
        container.planning_service.pin_budget_item.assert_called_once_with("expense", "Kira", 8000.0)

    def test_toggle_pin_false_calls_unpin_budget_item(self, qapp):
        container = _make_container()
        controller = CashflowController(container)
        controller.togglePinBudgetItem("expense", "Kira", 8000.0, False)
        container.planning_service.unpin_budget_item.assert_called_once_with("expense", "Kira")


class TestMonthSelection:
    def test_month_keys_are_twelve_recent_yyyy_mm(self, qapp):
        controller = CashflowController(_make_container())
        assert len(controller.monthKeys) == 12
        assert controller.monthKeys[0] == date.today().strftime("%Y-%m")

    def test_select_month_reloads_budget(self, qapp):
        container = _make_container()
        controller = CashflowController(container)
        other_month = controller.monthKeys[1]

        controller.selectMonth(other_month)

        assert controller.selectedMonth == other_month
        container.planning_service.get_budget_for_month.assert_any_call(other_month)

    def test_select_invalid_month_is_ignored(self, qapp):
        controller = CashflowController(_make_container())
        before = controller.selectedMonth
        controller.selectMonth("GECERSIZ")
        assert controller.selectedMonth == before


class TestGoals:
    def _goal(self, id=1, name="Araba", target="100000", current="20000", deadline=date(2027, 1, 1), priority="HIGH", status="ACTIVE"):
        return FinancialGoal(
            id=id, name=name, target_amount=Decimal(target), current_amount=Decimal(current),
            deadline=deadline, priority=priority, status=status,
        )

    def test_goal_lists_populated(self, qapp):
        controller = CashflowController(_make_container(goals=[self._goal()]))
        assert controller.goalNames == ["Araba"]
        assert controller.goalTargetAmounts == [100000.0]
        assert controller.goalCurrentAmounts == [20000.0]
        assert controller.goalProgressPct == pytest.approx([20.0])
        assert controller.goalDeadlines == ["2027-01-01"]

    def test_add_goal_delegates_and_refreshes(self, qapp):
        container = _make_container(goals=[])
        controller = CashflowController(container)
        container.planning_service.get_all_goals.return_value = [self._goal()]

        controller.addGoal("Araba", 100000.0, "2027-01-01", "HIGH")

        container.planning_service.add_goal.assert_called_once()
        assert controller.goalNames == ["Araba"]

    def test_add_goal_error_is_captured(self, qapp):
        container = _make_container()
        container.planning_service.add_goal.side_effect = ValueError("Hedef adı boş olamaz.")
        controller = CashflowController(container)

        controller.addGoal("", 100.0, "", "MEDIUM")

        assert controller.goalError == "Hedef adı boş olamaz."

    def test_contribute_to_goal_delegates_and_refreshes(self, qapp):
        container = _make_container(goals=[self._goal(current="20000")])
        controller = CashflowController(container)
        container.planning_service.get_all_goals.return_value = [self._goal(current="25000")]

        controller.contributeToGoal(1, 5000.0)

        container.planning_service.add_contribution.assert_called_once_with(1, 5000.0)
        assert controller.goalCurrentAmounts == [25000.0]

    def test_delete_goal_delegates_and_refreshes(self, qapp):
        container = _make_container(goals=[self._goal()])
        controller = CashflowController(container)
        container.planning_service.get_all_goals.return_value = []

        controller.deleteGoal(1)

        container.planning_service.delete_goal.assert_called_once_with(1)
        assert controller.goalNames == []


class TestFeasibility:
    def test_analysis_populates_properties(self, qapp):
        container = _make_container()
        container.planning_service.analyze_feasibility.return_value = {
            "status": "BAŞARILI", "monthly_power": 5000.0, "total_monthly_need": 3000.0, "details": [],
        }
        controller = CashflowController(container)

        controller.runFeasibilityAnalysis()

        assert controller.feasibilityStatus == "BAŞARILI"
        assert controller.feasibilityMonthlyPower == pytest.approx(5000.0)
        assert controller.feasibilityTotalMonthlyNeed == pytest.approx(3000.0)

    def test_no_active_goals_message(self, qapp):
        container = _make_container()
        container.planning_service.analyze_feasibility.return_value = {
            "status": "BİLGİ", "message": "Henüz aktif bir hedefiniz yok.",
        }
        controller = CashflowController(container)

        controller.runFeasibilityAnalysis()

        assert controller.feasibilityMessage == "Henüz aktif bir hedefiniz yok."
        assert controller.feasibilityMonthlyPower == 0.0


class TestCashMovements:
    def _movement(self, mtype, amount, d=date(2026, 1, 5), notes=None):
        creator = CashMovement.create_deposit if mtype == "DEPOSIT" else CashMovement.create_withdraw
        return creator(amount=Decimal(str(amount)), movement_date=d, movement_time=time(10, 0), notes=notes)

    def test_balance_and_movements_loaded(self, qapp):
        movements = [self._movement("DEPOSIT", 10000, notes="ilk yatırım")]
        controller = CashflowController(_make_container(movements=movements, cash_balance=Decimal("10000")))

        assert controller.cashBalance == pytest.approx(10000.0)
        assert controller.movementTypes == ["DEPOSIT"]
        assert controller.movementAmounts == [10000.0]
        assert controller.movementNotes == ["ilk yatırım"]

    def test_movements_sorted_most_recent_first(self, qapp):
        movements = [
            self._movement("DEPOSIT", 1000, d=date(2026, 1, 1)),
            self._movement("DEPOSIT", 2000, d=date(2026, 3, 1)),
            self._movement("WITHDRAW", 500, d=date(2026, 2, 1)),
        ]
        controller = CashflowController(_make_container(movements=movements))
        assert controller.movementAmounts == [2000.0, 500.0, 1000.0]

    def test_add_deposit_delegates_and_refreshes(self, qapp):
        container = _make_container()
        controller = CashflowController(container)
        container.cash_movement_service.get_movements.return_value = [self._movement("DEPOSIT", 5000)]
        container.cash_movement_service.get_cash_balance.return_value = Decimal("5000")

        controller.addDeposit(5000.0, "maaş")

        container.cash_movement_service.add_deposit.assert_called_once()
        assert controller.cashBalance == pytest.approx(5000.0)

    def test_add_withdraw_insufficient_balance_error_captured(self, qapp):
        container = _make_container()
        container.cash_movement_service.add_withdraw.side_effect = ValueError("Yetersiz nakit. Çekilecek: 100.00 TL, Mevcut: 0.00 TL")
        controller = CashflowController(container)

        controller.addWithdraw(100.0, "")

        assert "Yetersiz nakit" in controller.cashMovementError

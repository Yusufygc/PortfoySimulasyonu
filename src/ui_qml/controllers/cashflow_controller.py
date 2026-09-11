"""
CashflowController — CashflowView'un veri köprüsü (bkz. plan §7.3 madde 8, d6).

Mevcut `PlanningPage`'in (bütçe + hedef takibi) ve `CashMovementService`'in
(sermaye ekleme/çekme) QML karşılığı — üç alt bölüm tek görünümde: Bütçe,
Hedefler, Nakit Hareketleri. Hesap mantığı hiçbir yerde yeniden yazılmadı,
mevcut `PlanningService`/`CashMovementService`'e doğrudan delege edilir.

Kapsam notu (plan aslıyla karşılaştırıldığında dürüstçe belirtilen fark):
* Plan metni "Temettü ... giriş-çıkış akışı" diyor ama backend'de nakit
  hareketi olarak yalnızca `CashMovementType.DEPOSIT`/`WITHDRAW` var —
  temettü (dividend) için ayrı bir domain/servis kaydı YOK (`CorporateAction`
  yalnızca BEDELLİ/BEDELSİZ sermaye artırımını modelliyor, nakit temettü
  içermiyor). İcat edilmedi; bu görünüm yalnızca gerçekten var olan
  sermaye ekleme/çekme akışını gösterir.
* Hedef DÜZENLEME (`PlanningService.update_goal`, isim/tutar/vade değişikliği)
  v1 kapsamına alınmadı — sadece ekle/katkı yap/sil desteklenir (mevcut
  `WatchlistView`'daki "satır tıklama navigasyonu" gibi bilinçli, dar bir
  alt-küme; ihtiyaç netleşince eklenebilir).
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, List

from src.qt_compat.qtcore import Property, QObject, Signal, Slot
from src.domain.models.budget import Budget, BudgetItem

_MONTH_HISTORY_COUNT = 12


def _to_float(value: Any) -> float:
    return float(value) if value is not None else 0.0


def _recent_month_keys(today: date, count: int = _MONTH_HISTORY_COUNT) -> List[str]:
    keys: List[str] = []
    year, month = today.year, today.month
    for _ in range(count):
        keys.append(f"{year}-{month:02d}")
        month -= 1
        if month <= 0:
            month += 12
            year -= 1
    return keys


class CashflowController(QObject):
    """Bütçe + Finansal Hedefler + Nakit Hareketleri (sermaye ekleme/çekme)."""

    monthsChanged = Signal()
    budgetChanged = Signal()
    goalsChanged = Signal()
    feasibilityChanged = Signal()
    cashMovementsChanged = Signal()

    def __init__(self, container, parent=None) -> None:
        super().__init__(parent)
        self._container = container

        self._month_keys = _recent_month_keys(date.today())
        self._selected_month = self._month_keys[0]

        self._budget_item_types: List[str] = []
        self._budget_item_names: List[str] = []
        self._budget_item_amounts: List[float] = []
        self._savings_target = 0.0
        self._budget_error = ""

        self._pinned_item_types: List[str] = []
        self._pinned_item_names: List[str] = []
        self._pinned_item_amounts: List[float] = []

        self._goal_ids: List[int] = []
        self._goal_names: List[str] = []
        self._goal_target_amounts: List[float] = []
        self._goal_current_amounts: List[float] = []
        self._goal_priorities: List[str] = []
        self._goal_statuses: List[str] = []
        self._goal_deadlines: List[str] = []
        self._goal_error = ""

        self._feasibility_status = ""
        self._feasibility_message = ""
        self._feasibility_monthly_power = 0.0
        self._feasibility_total_monthly_need = 0.0

        self._cash_balance = 0.0
        self._movement_dates: List[str] = []
        self._movement_types: List[str] = []
        self._movement_amounts: List[float] = []
        self._movement_notes: List[str] = []
        self._cash_movement_error = ""

        self._load_month(self._selected_month)
        self.refreshGoals()
        self.refreshCashMovements()

    # ==================== Bütçe ==================== #

    @Property("QVariantList", constant=True)
    def monthKeys(self) -> List[str]:
        return list(self._month_keys)

    @Property(str, notify=monthsChanged)
    def selectedMonth(self) -> str:
        return self._selected_month

    @Slot(str)
    def selectMonth(self, month: str) -> None:
        if month not in self._month_keys or month == self._selected_month:
            return
        self._selected_month = month
        self.monthsChanged.emit()
        self._load_month(month)

    @Property("QVariantList", notify=budgetChanged)
    def budgetItemTypes(self) -> List[str]:
        return list(self._budget_item_types)

    @Property("QVariantList", notify=budgetChanged)
    def budgetItemNames(self) -> List[str]:
        return list(self._budget_item_names)

    @Property("QVariantList", notify=budgetChanged)
    def budgetItemAmounts(self) -> List[float]:
        return list(self._budget_item_amounts)

    @Property(float, notify=budgetChanged)
    def savingsTarget(self) -> float:
        return self._savings_target

    @Slot(float)
    def setSavingsTarget(self, value: float) -> None:
        if value != self._savings_target:
            self._savings_target = value
            self._recompute_budget_totals()

    @Property(float, notify=budgetChanged)
    def totalIncome(self) -> float:
        return self._current_budget_snapshot().total_income_float

    @Property(float, notify=budgetChanged)
    def totalExpense(self) -> float:
        return self._current_budget_snapshot().total_expense_float

    @Property(float, notify=budgetChanged)
    def netSavingsPotential(self) -> float:
        return self._current_budget_snapshot().net_savings_potential_float

    @Property(str, notify=budgetChanged)
    def budgetStatusMessage(self) -> str:
        return self._current_budget_snapshot().status_message

    @Property(str, notify=budgetChanged)
    def budgetError(self) -> str:
        return self._budget_error

    @Property("QVariantList", notify=budgetChanged)
    def pinnedItemTypes(self) -> List[str]:
        return list(self._pinned_item_types)

    @Property("QVariantList", notify=budgetChanged)
    def pinnedItemNames(self) -> List[str]:
        return list(self._pinned_item_names)

    @Property("QVariantList", notify=budgetChanged)
    def pinnedItemAmounts(self) -> List[float]:
        return list(self._pinned_item_amounts)

    @Slot(str, str, float)
    def addBudgetItem(self, item_type: str, name: str, amount: float) -> None:
        if item_type not in ("income", "expense") or not name.strip() or amount <= 0:
            return
        self._budget_item_types.append(item_type)
        self._budget_item_names.append(name.strip())
        self._budget_item_amounts.append(amount)
        self._recompute_budget_totals()

    @Slot(int)
    def removeBudgetItem(self, index: int) -> None:
        if 0 <= index < len(self._budget_item_types):
            del self._budget_item_types[index]
            del self._budget_item_names[index]
            del self._budget_item_amounts[index]
            self._recompute_budget_totals()

    @Slot()
    def saveBudget(self) -> None:
        try:
            budget = self._build_budget_domain_object()
        except ValueError as exc:
            self._budget_error = str(exc)
            self.budgetChanged.emit()
            return

        try:
            self._container.planning_service.save_budget(budget)
        except Exception as exc:
            self._budget_error = str(exc)
            self.budgetChanged.emit()
            return

        self._budget_error = ""
        self.budgetChanged.emit()

    @Slot(str, str, float, bool)
    def togglePinBudgetItem(self, item_type: str, name: str, amount: float, pinned: bool) -> None:
        planning = self._container.planning_service
        try:
            if pinned:
                planning.pin_budget_item(item_type, name, amount)
            else:
                planning.unpin_budget_item(item_type, name)
        except Exception as exc:
            self._budget_error = str(exc)
            self.budgetChanged.emit()
            return
        self._refresh_pinned_items()
        self.budgetChanged.emit()

    def _load_month(self, month: str) -> None:
        planning = self._container.planning_service
        self._refresh_pinned_items()

        budget = planning.get_budget_for_month(month)
        if budget is None:
            budget = planning.get_budget_draft_from_pinned_items(month)

        self._budget_item_types = [item.item_type for item in budget.items]
        self._budget_item_names = [item.name for item in budget.items]
        self._budget_item_amounts = [_to_float(item.amount) for item in budget.items]
        self._savings_target = _to_float(budget.savings_target)
        self._budget_error = ""
        self.budgetChanged.emit()

    def _refresh_pinned_items(self) -> None:
        pinned = self._container.planning_service.get_pinned_budget_items()
        self._pinned_item_types = [item.item_type for item in pinned]
        self._pinned_item_names = [item.name for item in pinned]
        self._pinned_item_amounts = [_to_float(item.default_amount) for item in pinned]

    def _recompute_budget_totals(self) -> None:
        self._budget_error = ""
        self.budgetChanged.emit()

    def _build_budget_domain_object(self) -> Budget:
        items = [
            BudgetItem(id=None, budget_id=None, item_type=item_type, name=name, amount=Decimal(str(amount)))
            for item_type, name, amount in zip(
                self._budget_item_types, self._budget_item_names, self._budget_item_amounts,
            )
        ]
        return Budget(id=None, month=self._selected_month, savings_target=Decimal(str(self._savings_target)), items=items)

    def _current_budget_snapshot(self) -> "_BudgetSnapshot":
        try:
            budget = self._build_budget_domain_object()
        except ValueError:
            return _BudgetSnapshot(0.0, 0.0, 0.0, "")
        return _BudgetSnapshot(
            total_income_float=_to_float(budget.total_income),
            total_expense_float=_to_float(budget.total_expense),
            net_savings_potential_float=_to_float(budget.net_savings_potential),
            status_message=budget.status_message,
        )

    # ==================== Hedefler ==================== #

    @Property("QVariantList", notify=goalsChanged)
    def goalIds(self) -> List[int]:
        return list(self._goal_ids)

    @Property("QVariantList", notify=goalsChanged)
    def goalNames(self) -> List[str]:
        return list(self._goal_names)

    @Property("QVariantList", notify=goalsChanged)
    def goalTargetAmounts(self) -> List[float]:
        return list(self._goal_target_amounts)

    @Property("QVariantList", notify=goalsChanged)
    def goalCurrentAmounts(self) -> List[float]:
        return list(self._goal_current_amounts)

    @Property("QVariantList", notify=goalsChanged)
    def goalProgressPct(self) -> List[float]:
        return [
            (current / target * 100.0) if target > 0 else 0.0
            for current, target in zip(self._goal_current_amounts, self._goal_target_amounts)
        ]

    @Property("QVariantList", notify=goalsChanged)
    def goalPriorities(self) -> List[str]:
        return list(self._goal_priorities)

    @Property("QVariantList", notify=goalsChanged)
    def goalStatuses(self) -> List[str]:
        return list(self._goal_statuses)

    @Property("QVariantList", notify=goalsChanged)
    def goalDeadlines(self) -> List[str]:
        return list(self._goal_deadlines)

    @Property(str, notify=goalsChanged)
    def goalError(self) -> str:
        return self._goal_error

    @Slot(str, float, str, str)
    def addGoal(self, name: str, target_amount: float, deadline_iso: str, priority: str) -> None:
        try:
            deadline = date.fromisoformat(deadline_iso) if deadline_iso else None
            self._container.planning_service.add_goal(
                name=name, target_amount=target_amount, deadline=deadline, priority=priority or "MEDIUM",
            )
        except Exception as exc:
            self._goal_error = str(exc)
            self.goalsChanged.emit()
            return
        self.refreshGoals()

    @Slot(int, float)
    def contributeToGoal(self, goal_id: int, amount: float) -> None:
        try:
            self._container.planning_service.add_contribution(goal_id, amount)
        except Exception as exc:
            self._goal_error = str(exc)
            self.goalsChanged.emit()
            return
        self.refreshGoals()

    @Slot(int)
    def deleteGoal(self, goal_id: int) -> None:
        try:
            self._container.planning_service.delete_goal(goal_id)
        except Exception as exc:
            self._goal_error = str(exc)
            self.goalsChanged.emit()
            return
        self.refreshGoals()

    @Slot()
    def refreshGoals(self) -> None:
        goals = self._container.planning_service.get_all_goals()
        self._goal_ids = [g.id for g in goals]
        self._goal_names = [g.name for g in goals]
        self._goal_target_amounts = [_to_float(g.target_amount) for g in goals]
        self._goal_current_amounts = [_to_float(g.current_amount) for g in goals]
        self._goal_priorities = [g.priority for g in goals]
        self._goal_statuses = [g.status for g in goals]
        self._goal_deadlines = [g.deadline.isoformat() if g.deadline else "" for g in goals]
        self._goal_error = ""
        self.goalsChanged.emit()

    @Property(str, notify=feasibilityChanged)
    def feasibilityStatus(self) -> str:
        return self._feasibility_status

    @Property(str, notify=feasibilityChanged)
    def feasibilityMessage(self) -> str:
        return self._feasibility_message

    @Property(float, notify=feasibilityChanged)
    def feasibilityMonthlyPower(self) -> float:
        return self._feasibility_monthly_power

    @Property(float, notify=feasibilityChanged)
    def feasibilityTotalMonthlyNeed(self) -> float:
        return self._feasibility_total_monthly_need

    @Slot()
    def runFeasibilityAnalysis(self) -> None:
        result = self._container.planning_service.analyze_feasibility()
        self._feasibility_status = result.get("status", "")
        self._feasibility_message = result.get("message", "")
        self._feasibility_monthly_power = _to_float(result.get("monthly_power"))
        self._feasibility_total_monthly_need = _to_float(result.get("total_monthly_need"))
        self.feasibilityChanged.emit()

    # ==================== Nakit Hareketleri ==================== #

    @Property(float, notify=cashMovementsChanged)
    def cashBalance(self) -> float:
        return self._cash_balance

    @Property("QVariantList", notify=cashMovementsChanged)
    def movementDates(self) -> List[str]:
        return list(self._movement_dates)

    @Property("QVariantList", notify=cashMovementsChanged)
    def movementTypes(self) -> List[str]:
        return list(self._movement_types)

    @Property("QVariantList", notify=cashMovementsChanged)
    def movementAmounts(self) -> List[float]:
        return list(self._movement_amounts)

    @Property("QVariantList", notify=cashMovementsChanged)
    def movementNotes(self) -> List[str]:
        return list(self._movement_notes)

    @Property(str, notify=cashMovementsChanged)
    def cashMovementError(self) -> str:
        return self._cash_movement_error

    @Slot(float, str)
    def addDeposit(self, amount: float, notes: str) -> None:
        try:
            self._container.cash_movement_service.add_deposit(Decimal(str(amount)), notes=notes or None)
        except Exception as exc:
            self._cash_movement_error = str(exc)
            self.cashMovementsChanged.emit()
            return
        self.refreshCashMovements()

    @Slot(float, str)
    def addWithdraw(self, amount: float, notes: str) -> None:
        try:
            self._container.cash_movement_service.add_withdraw(Decimal(str(amount)), notes=notes or None)
        except Exception as exc:
            self._cash_movement_error = str(exc)
            self.cashMovementsChanged.emit()
            return
        self.refreshCashMovements()

    @Slot()
    def refreshCashMovements(self) -> None:
        service = self._container.cash_movement_service
        movements = sorted(service.get_movements(), key=lambda m: (m.movement_date, m.movement_time or datetime.min.time()), reverse=True)
        self._cash_balance = _to_float(service.get_cash_balance())
        self._movement_dates = [m.movement_date.isoformat() for m in movements]
        self._movement_types = [m.type.value for m in movements]
        self._movement_amounts = [_to_float(m.amount) for m in movements]
        self._movement_notes = [m.notes or "" for m in movements]
        self._cash_movement_error = ""
        self.cashMovementsChanged.emit()


class _BudgetSnapshot:
    __slots__ = ("total_income_float", "total_expense_float", "net_savings_potential_float", "status_message")

    def __init__(self, total_income_float, total_expense_float, net_savings_potential_float, status_message) -> None:
        self.total_income_float = total_income_float
        self.total_expense_float = total_expense_float
        self.net_savings_potential_float = net_savings_potential_float
        self.status_message = status_message

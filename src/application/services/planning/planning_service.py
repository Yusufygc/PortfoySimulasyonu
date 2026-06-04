# src/application/services/planning_service.py

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from src.domain.models.budget import Budget, BudgetItem, BudgetPinnedItem
from src.domain.models.financial_goal import FinancialGoal, GoalStatus
from src.domain.ports.repositories.i_planning_repo import IPlanningRepository


def _to_decimal(value: Decimal | float | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class PlanningService:
    """
    Finansal Planlama iş mantığı servisi.

    İki ana modülü yönetir:
        1. Bütçe Yönetimi: Aylık gelir/gider kaydı ve tasarruf analizi
        2. Hedef Takibi: Finansal hedef CRUD, katkı ekleme ve fizibilite analizi
    """

    def __init__(self, planning_repo: IPlanningRepository) -> None:
        self._repo = planning_repo

    # ==================== Bütçe Yönetimi ==================== #

    def get_budget_for_month(self, month: str) -> Optional[Budget]:
        """Belirtilen ay için bütçe kaydını döner."""
        return self._repo.get_budget_by_month(month)

    def get_all_budgets(self) -> List[Budget]:
        """Tüm bütçe kayıtlarını döner."""
        return self._repo.get_all_budgets()

    def save_budget(self, budget: Budget) -> Budget:
        """
        Bütçe kaydını oluşturur veya günceller.

        Args:
            budget: Kaydedilecek Budget nesnesi (items listesi dahil)

        Returns:
            Kaydedilen Budget nesnesi
        """
        if not budget.month or len(budget.month) != 7:
            raise ValueError("Ay formatı 'YYYY-MM' olmalıdır.")
        return self._repo.upsert_budget(budget)

    def get_monthly_analysis(self, month: str) -> Optional[Dict[str, Any]]:
        """
        Bir ayın finansal röntgenini döner.

        Returns:
            Dict: total_income, total_expense, net_potential, target, message
            veya None (kayıt yoksa)
        """
        budget = self._repo.get_budget_by_month(month)
        if budget is None:
            return None

        return {
            "month": budget.month,
            "total_income": float(budget.total_income),
            "total_expense": float(budget.total_expense),
            "net_potential": float(budget.net_savings_potential),
            "target": float(budget.savings_target),
            "breakdown": {item.name: float(item.amount) for item in budget.items},
            "message": budget.status_message,
        }

    def delete_budget(self, budget_id: int) -> None:
        """Bütçe kaydını siler."""
        self._repo.delete_budget(budget_id)

    def get_pinned_budget_items(self) -> List[BudgetPinnedItem]:
        """Tekrarlanan bütçe kalemi şablonlarını döner."""
        return self._repo.get_pinned_budget_items()

    def pin_budget_item(self, item_type: str, name: str, amount: float) -> BudgetPinnedItem:
        """Gelir/gider kalemini sonraki boş aylar için şablon olarak kaydeder."""
        pinned_item = BudgetPinnedItem(
            id=None,
            item_type=item_type,
            name=name,
            default_amount=_to_decimal(amount),
        )
        return self._repo.upsert_pinned_budget_item(pinned_item)

    def unpin_budget_item(self, item_type: str, name: str) -> None:
        """Gelir/gider kalemi şablonunu kaldırır."""
        BudgetPinnedItem(id=None, item_type=item_type, name=name, default_amount=Decimal("0"))
        self._repo.delete_pinned_budget_item(item_type, name.strip())

    def get_budget_draft_from_pinned_items(self, month: str) -> Budget:
        """Kayıtlı bütçesi olmayan aylar için pinli kalemlerden taslak bütçe üretir."""
        if not month or len(month) != 7:
            raise ValueError("Ay formatı 'YYYY-MM' olmalıdır.")
        return Budget(
            id=None,
            month=month,
            savings_target=Decimal("0"),
            items=[
                BudgetItem(
                    id=None,
                    budget_id=None,
                    item_type=item.item_type,
                    name=item.name,
                    amount=item.default_amount,
                )
                for item in self._repo.get_pinned_budget_items()
            ],
        )

    # ==================== Hedef Takibi ==================== #

    def get_all_goals(self) -> List[FinancialGoal]:
        """Tüm hedefleri döner."""
        return self._repo.get_all_goals()

    def get_active_goals(self) -> List[FinancialGoal]:
        """Sadece aktif hedefleri döner."""
        return self._repo.get_active_goals()

    def add_goal(
        self,
        name: str,
        target_amount: float,
        deadline: date,
        priority: str = "MEDIUM",
    ) -> FinancialGoal:
        """
        Yeni bir finansal hedef ekler.

        Args:
            name: Hedef adı (Araba, Ev, Tatil ...)
            target_amount: Hedef tutar (TL)
            deadline: Hedef bitiş tarihi
            priority: LOW / MEDIUM / HIGH

        Returns:
            Oluşturulan FinancialGoal
        """
        if not name or not name.strip():
            raise ValueError("Hedef adı boş olamaz.")

        target_amount_decimal = _to_decimal(target_amount)
        if target_amount_decimal <= 0:
            raise ValueError("Hedef tutar pozitif olmalıdır.")

        goal = FinancialGoal(
            id=None,
            name=name.strip(),
            target_amount=target_amount_decimal,
            current_amount=Decimal("0"),
            deadline=deadline,
            priority=priority,
            status=GoalStatus.ACTIVE,
        )
        return self._repo.insert_goal(goal)

    def update_goal(
        self,
        goal_id: int,
        name: str,
        target_amount: float,
        deadline: date,
        priority: str = "MEDIUM",
    ) -> None:
        """Mevcut hedefi günceller."""
        existing = self._repo.get_goal_by_id(goal_id)
        if existing is None:
            raise ValueError(f"Hedef bulunamadı: {goal_id}")

        updated = FinancialGoal(
            id=goal_id,
            name=name.strip(),
            target_amount=_to_decimal(target_amount),
            current_amount=existing.current_amount,
            deadline=deadline,
            priority=priority,
            status=existing.status,
        )
        self._repo.update_goal(updated)

    def delete_goal(self, goal_id: int) -> None:
        """Hedefi siler."""
        self._repo.delete_goal(goal_id)

    def add_contribution(self, goal_id: int, amount: float) -> FinancialGoal:
        """
        Hedefe katkı (para) ekler.
        Hedef tutarına ulaşılırsa otomatik olarak COMPLETED olarak işaretler.

        Args:
            goal_id: Hedef ID
            amount: Eklenecek tutar (TL)

        Returns:
            Güncellenmiş FinancialGoal
        """
        amount_decimal = _to_decimal(amount)
        if amount_decimal <= 0:
            raise ValueError("Katkı tutarı pozitif olmalıdır.")

        goal = self._repo.get_goal_by_id(goal_id)
        if goal is None:
            raise ValueError(f"Hedef bulunamadı: {goal_id}")

        new_amount = goal.current_amount + amount_decimal
        new_status = GoalStatus.COMPLETED if new_amount >= goal.target_amount else goal.status

        updated = FinancialGoal(
            id=goal.id,
            name=goal.name,
            target_amount=goal.target_amount,
            current_amount=new_amount,
            deadline=goal.deadline,
            priority=goal.priority,
            status=new_status,
        )
        self._repo.update_goal(updated)
        return updated

    def analyze_feasibility(self) -> Dict[str, Any]:
        """
        Mevcut tasarruf gücüne göre hedeflere ulaşılabilirliği analiz eder.

        En son bütçe kaydındaki tasarruf potansiyelini baz alır.

        Returns:
            Dict: status, monthly_power, total_monthly_need, details[]
        """
        active_goals = self._repo.get_active_goals()
        if not active_goals:
            return {"status": "BİLGİ", "message": "Henüz aktif bir hedefiniz yok."}

        monthly_power = self._latest_monthly_savings_power()

        if monthly_power <= 0:
            return {
                "status": "KRİTİK",
                "message": "Aylık tasarruf gücünüz 0 veya negatif. Hedeflere ulaşmanız çok zor.",
                "monthly_power": monthly_power,
                "total_monthly_need": 0.0,
                "details": [],
            }

        details = [self._goal_feasibility_detail(goal, monthly_power) for goal in active_goals]
        total_monthly_need = sum(detail["required_monthly"] for detail in details)
        overall_status = "BAŞARILI" if monthly_power >= total_monthly_need else "YETERSİZ KAYNAK"

        return {
            "status": overall_status,
            "monthly_power": monthly_power,
            "total_monthly_need": total_monthly_need,
            "details": details,
        }

    def _latest_monthly_savings_power(self) -> float:
        all_budgets = self._repo.get_all_budgets()
        if not all_budgets:
            return 0.0
        latest_budget = all_budgets[0]  # DESC sıralı, ilk eleman en güncel
        return float(latest_budget.net_savings_potential)

    @staticmethod
    def _goal_feasibility_detail(goal: FinancialGoal, monthly_power: float) -> Dict[str, Any]:
        required_monthly = float(goal.required_monthly_contribution())
        is_possible = monthly_power >= required_monthly

        return {
            "goal_id": goal.id,
            "goal_name": goal.name,
            "target": float(goal.target_amount),
            "saved": float(goal.current_amount),
            "remaining": float(goal.remaining_amount),
            "progress": goal.progress_ratio,
            "months_left": goal.months_remaining(),
            "required_monthly": required_monthly,
            "status": "YETİŞİR" if is_possible else "RİSKLİ",
        }

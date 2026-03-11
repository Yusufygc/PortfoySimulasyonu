# src/application/services/planning_service.py

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from src.domain.models.budget import Budget
from src.domain.models.financial_goal import FinancialGoal, GoalStatus
from src.domain.services_interfaces.i_planning_repo import IPlanningRepository


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

    def save_budget(
        self,
        month: str,
        income_salary: float = 0.0,
        income_additional: float = 0.0,
        expense_rent: float = 0.0,
        expense_bills: float = 0.0,
        expense_food: float = 0.0,
        expense_transport: float = 0.0,
        expense_luxury: float = 0.0,
        savings_target: float = 0.0,
    ) -> Budget:
        """
        Bütçe kaydını oluşturur veya günceller.

        Args:
            month: 'YYYY-MM' formatında ay
            Diğer parametreler: Gelir/gider kalemleri ve tasarruf hedefi

        Returns:
            Kaydedilen Budget nesnesi
        """
        if not month or len(month) != 7:
            raise ValueError("Ay formatı 'YYYY-MM' olmalıdır.")

        budget = Budget(
            id=None,
            month=month,
            income_salary=income_salary,
            income_additional=income_additional,
            expense_rent=expense_rent,
            expense_bills=expense_bills,
            expense_food=expense_food,
            expense_transport=expense_transport,
            expense_luxury=expense_luxury,
            savings_target=savings_target,
        )
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
            "total_income": budget.total_income,
            "total_expense": budget.total_expense,
            "net_potential": budget.net_savings_potential,
            "target": budget.savings_target,
            "breakdown": {
                "rent": budget.expense_rent,
                "bills": budget.expense_bills,
                "food": budget.expense_food,
                "transport": budget.expense_transport,
                "luxury": budget.expense_luxury,
            },
            "message": budget.status_message,
        }

    def delete_budget(self, budget_id: int) -> None:
        """Bütçe kaydını siler."""
        self._repo.delete_budget(budget_id)

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

        if target_amount <= 0:
            raise ValueError("Hedef tutar pozitif olmalıdır.")

        goal = FinancialGoal(
            id=None,
            name=name.strip(),
            target_amount=target_amount,
            current_amount=0.0,
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
            target_amount=target_amount,
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
        if amount <= 0:
            raise ValueError("Katkı tutarı pozitif olmalıdır.")

        goal = self._repo.get_goal_by_id(goal_id)
        if goal is None:
            raise ValueError(f"Hedef bulunamadı: {goal_id}")

        new_amount = goal.current_amount + amount
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

        # Son bütçe kaydından tasarruf gücünü hesapla
        all_budgets = self._repo.get_all_budgets()
        monthly_power = 0.0

        if all_budgets:
            latest_budget = all_budgets[0]  # DESC sıralı, ilk eleman en güncel
            monthly_power = latest_budget.net_savings_potential

        if monthly_power <= 0:
            return {
                "status": "KRİTİK",
                "message": "Aylık tasarruf gücünüz 0 veya negatif. Hedeflere ulaşmanız çok zor.",
                "monthly_power": monthly_power,
                "total_monthly_need": 0.0,
                "details": [],
            }

        # Hedef bazlı analiz
        details = []
        total_monthly_need = 0.0

        for goal in active_goals:
            required_monthly = goal.required_monthly_contribution()
            total_monthly_need += required_monthly

            is_possible = monthly_power >= required_monthly

            details.append({
                "goal_id": goal.id,
                "goal_name": goal.name,
                "target": goal.target_amount,
                "saved": goal.current_amount,
                "remaining": goal.remaining_amount,
                "progress": goal.progress_ratio,
                "months_left": goal.months_remaining(),
                "required_monthly": required_monthly,
                "status": "YETİŞİR" if is_possible else "RİSKLİ",
            })

        overall_status = "BAŞARILI" if monthly_power >= total_monthly_need else "YETERSİZ KAYNAK"

        return {
            "status": overall_status,
            "monthly_power": monthly_power,
            "total_monthly_need": total_monthly_need,
            "details": details,
        }

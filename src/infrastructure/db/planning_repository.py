# src/infrastructure/db/planning_repository.py

from __future__ import annotations

from datetime import date
from typing import List, Optional

from src.domain.models.budget import Budget
from src.domain.models.financial_goal import FinancialGoal
from src.domain.services_interfaces.i_planning_repo import IPlanningRepository
from .mysql_connection import MySQLConnectionProvider


class MySQLPlanningRepository(IPlanningRepository):
    """
    IPlanningRepository'nin MySQL implementasyonu.
    'budgets' ve 'financial_goals' tablolarına erişir.
    """

    def __init__(self, connection_provider: MySQLConnectionProvider) -> None:
        self._cp = connection_provider

    # ==================== Row → Domain Mappers ==================== #

    @staticmethod
    def _row_to_budget(row: dict) -> Budget:
        return Budget(
            id=row["id"],
            month=row["month"],
            income_salary=float(row.get("income_salary", 0) or 0),
            income_additional=float(row.get("income_additional", 0) or 0),
            expense_rent=float(row.get("expense_rent", 0) or 0),
            expense_bills=float(row.get("expense_bills", 0) or 0),
            expense_food=float(row.get("expense_food", 0) or 0),
            expense_transport=float(row.get("expense_transport", 0) or 0),
            expense_luxury=float(row.get("expense_luxury", 0) or 0),
            savings_target=float(row.get("savings_target", 0) or 0),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    @staticmethod
    def _row_to_goal(row: dict) -> FinancialGoal:
        deadline_val = row.get("deadline")
        if isinstance(deadline_val, str):
            deadline_val = date.fromisoformat(deadline_val)

        return FinancialGoal(
            id=row["id"],
            name=row["name"],
            target_amount=float(row.get("target_amount", 0) or 0),
            current_amount=float(row.get("current_amount", 0) or 0),
            deadline=deadline_val,
            priority=row.get("priority", "MEDIUM"),
            status=row.get("status", "ACTIVE"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    # ==================== Budget İşlemleri ==================== #

    def get_budget_by_month(self, month: str) -> Optional[Budget]:
        sql = """
            SELECT id, month, income_salary, income_additional,
                   expense_rent, expense_bills, expense_food,
                   expense_transport, expense_luxury, savings_target,
                   created_at, updated_at
            FROM budgets
            WHERE month = %s
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (month,))
            row = cursor.fetchone()

        if row is None:
            return None
        return self._row_to_budget(row)

    def get_all_budgets(self) -> List[Budget]:
        sql = """
            SELECT id, month, income_salary, income_additional,
                   expense_rent, expense_bills, expense_food,
                   expense_transport, expense_luxury, savings_target,
                   created_at, updated_at
            FROM budgets
            ORDER BY month DESC
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql)
            rows = cursor.fetchall()

        return [self._row_to_budget(r) for r in rows]

    def upsert_budget(self, budget: Budget) -> Budget:
        # Aynı ay için kayıt var mı kontrol et
        existing = self.get_budget_by_month(budget.month)

        if existing:
            # Güncelle
            sql = """
                UPDATE budgets
                SET income_salary = %s, income_additional = %s,
                    expense_rent = %s, expense_bills = %s, expense_food = %s,
                    expense_transport = %s, expense_luxury = %s,
                    savings_target = %s
                WHERE id = %s
            """
            with self._cp.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (
                    budget.income_salary, budget.income_additional,
                    budget.expense_rent, budget.expense_bills, budget.expense_food,
                    budget.expense_transport, budget.expense_luxury,
                    budget.savings_target,
                    existing.id,
                ))

            budget_id = existing.id
        else:
            # Yeni oluştur
            sql = """
                INSERT INTO budgets
                    (month, income_salary, income_additional,
                     expense_rent, expense_bills, expense_food,
                     expense_transport, expense_luxury, savings_target)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            with self._cp.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (
                    budget.month,
                    budget.income_salary, budget.income_additional,
                    budget.expense_rent, budget.expense_bills, budget.expense_food,
                    budget.expense_transport, budget.expense_luxury,
                    budget.savings_target,
                ))
                budget_id = cursor.lastrowid

        return Budget(
            id=budget_id,
            month=budget.month,
            income_salary=budget.income_salary,
            income_additional=budget.income_additional,
            expense_rent=budget.expense_rent,
            expense_bills=budget.expense_bills,
            expense_food=budget.expense_food,
            expense_transport=budget.expense_transport,
            expense_luxury=budget.expense_luxury,
            savings_target=budget.savings_target,
        )

    def delete_budget(self, budget_id: int) -> None:
        sql = "DELETE FROM budgets WHERE id = %s"
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (budget_id,))

    # ==================== FinancialGoal İşlemleri ==================== #

    def get_all_goals(self) -> List[FinancialGoal]:
        sql = """
            SELECT id, name, target_amount, current_amount,
                   deadline, priority, status, created_at, updated_at
            FROM financial_goals
            ORDER BY deadline ASC
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql)
            rows = cursor.fetchall()

        return [self._row_to_goal(r) for r in rows]

    def get_active_goals(self) -> List[FinancialGoal]:
        sql = """
            SELECT id, name, target_amount, current_amount,
                   deadline, priority, status, created_at, updated_at
            FROM financial_goals
            WHERE status = 'ACTIVE'
            ORDER BY deadline ASC
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql)
            rows = cursor.fetchall()

        return [self._row_to_goal(r) for r in rows]

    def get_goal_by_id(self, goal_id: int) -> Optional[FinancialGoal]:
        sql = """
            SELECT id, name, target_amount, current_amount,
                   deadline, priority, status, created_at, updated_at
            FROM financial_goals
            WHERE id = %s
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, (goal_id,))
            row = cursor.fetchone()

        if row is None:
            return None
        return self._row_to_goal(row)

    def insert_goal(self, goal: FinancialGoal) -> FinancialGoal:
        sql = """
            INSERT INTO financial_goals
                (name, target_amount, current_amount, deadline, priority, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (
                goal.name, goal.target_amount, goal.current_amount,
                goal.deadline, goal.priority, goal.status,
            ))
            goal_id = cursor.lastrowid

        return FinancialGoal(
            id=goal_id,
            name=goal.name,
            target_amount=goal.target_amount,
            current_amount=goal.current_amount,
            deadline=goal.deadline,
            priority=goal.priority,
            status=goal.status,
        )

    def update_goal(self, goal: FinancialGoal) -> None:
        if goal.id is None:
            raise ValueError("Goal id is required for update")

        sql = """
            UPDATE financial_goals
            SET name = %s, target_amount = %s, current_amount = %s,
                deadline = %s, priority = %s, status = %s
            WHERE id = %s
        """
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (
                goal.name, goal.target_amount, goal.current_amount,
                goal.deadline, goal.priority, goal.status,
                goal.id,
            ))

    def delete_goal(self, goal_id: int) -> None:
        sql = "DELETE FROM financial_goals WHERE id = %s"
        with self._cp.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (goal_id,))

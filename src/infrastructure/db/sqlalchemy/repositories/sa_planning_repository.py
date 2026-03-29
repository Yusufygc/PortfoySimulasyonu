# src/infrastructure/db/sqlalchemy/repositories/sa_planning_repository.py

from datetime import date
from typing import List, Optional
from src.domain.models.budget import Budget
from src.domain.models.financial_goal import FinancialGoal
from src.domain.services_interfaces.i_planning_repo import IPlanningRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMBudget, ORMFinancialGoal

class SQLAlchemyPlanningRepository(IPlanningRepository):
    """
    IPlanningRepository arayüzünün SQLAlchemy tabanlı uygulaması.
    """

    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    # ==================== Row → Domain Mappers ==================== #
    def _to_domain_budget(self, orm: ORMBudget) -> Budget:
        return Budget(
            id=orm.id,
            month=orm.month,
            income_salary=float(orm.income_salary),
            income_additional=float(orm.income_additional),
            expense_rent=float(orm.expense_rent),
            expense_bills=float(orm.expense_bills),
            expense_food=float(orm.expense_food),
            expense_transport=float(orm.expense_transport),
            expense_luxury=float(orm.expense_luxury),
            savings_target=float(orm.savings_target),
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def _to_orm_budget(self, domain: Budget) -> ORMBudget:
        return ORMBudget(
            id=domain.id,
            month=domain.month,
            income_salary=domain.income_salary,
            income_additional=domain.income_additional,
            expense_rent=domain.expense_rent,
            expense_bills=domain.expense_bills,
            expense_food=domain.expense_food,
            expense_transport=domain.expense_transport,
            expense_luxury=domain.expense_luxury,
            savings_target=domain.savings_target,
        )

    def _to_domain_goal(self, orm: ORMFinancialGoal) -> FinancialGoal:
        return FinancialGoal(
            id=orm.id,
            name=orm.name,
            target_amount=float(orm.target_amount),
            current_amount=float(orm.current_amount),
            deadline=orm.deadline,
            priority=orm.priority,
            status=orm.status,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def _to_orm_goal(self, domain: FinancialGoal) -> ORMFinancialGoal:
        return ORMFinancialGoal(
            id=domain.id,
            name=domain.name,
            target_amount=domain.target_amount,
            current_amount=domain.current_amount,
            deadline=domain.deadline,
            priority=domain.priority,
            status=domain.status,
        )

    # ==================== Budget İşlemleri ==================== #
    def get_budget_by_month(self, month: str) -> Optional[Budget]:
        with self._provider.get_session() as session:
            row = session.query(ORMBudget).filter_by(month=month).first()
            return self._to_domain_budget(row) if row else None

    def get_all_budgets(self) -> List[Budget]:
        with self._provider.get_session() as session:
            rows = session.query(ORMBudget).order_by(ORMBudget.month.desc()).all()
            return [self._to_domain_budget(r) for r in rows]

    def upsert_budget(self, budget: Budget) -> Budget:
        with self._provider.get_session() as session:
            # Check exist
            orm_obj = session.query(ORMBudget).filter_by(month=budget.month).first()
            if orm_obj:
                orm_obj.income_salary = budget.income_salary
                orm_obj.income_additional = budget.income_additional
                orm_obj.expense_rent = budget.expense_rent
                orm_obj.expense_bills = budget.expense_bills
                orm_obj.expense_food = budget.expense_food
                orm_obj.expense_transport = budget.expense_transport
                orm_obj.expense_luxury = budget.expense_luxury
                orm_obj.savings_target = budget.savings_target
            else:
                orm_obj = self._to_orm_budget(budget)
                session.add(orm_obj)
            
            session.commit()
            session.refresh(orm_obj)
            return self._to_domain_budget(orm_obj)

    def delete_budget(self, budget_id: int) -> None:
        with self._provider.get_session() as session:
            orm_obj = session.query(ORMBudget).filter_by(id=budget_id).first()
            if orm_obj:
                session.delete(orm_obj)
                session.commit()

    # ==================== FinancialGoal İşlemleri ==================== #
    def get_all_goals(self) -> List[FinancialGoal]:
        with self._provider.get_session() as session:
            rows = session.query(ORMFinancialGoal).order_by(ORMFinancialGoal.deadline.asc()).all()
            return [self._to_domain_goal(r) for r in rows]

    def get_active_goals(self) -> List[FinancialGoal]:
        with self._provider.get_session() as session:
            rows = session.query(ORMFinancialGoal).filter_by(status="ACTIVE").order_by(ORMFinancialGoal.deadline.asc()).all()
            return [self._to_domain_goal(r) for r in rows]

    def get_goal_by_id(self, goal_id: int) -> Optional[FinancialGoal]:
        with self._provider.get_session() as session:
            row = session.query(ORMFinancialGoal).filter_by(id=goal_id).first()
            return self._to_domain_goal(row) if row else None

    def insert_goal(self, goal: FinancialGoal) -> FinancialGoal:
        with self._provider.get_session() as session:
            orm_obj = self._to_orm_goal(goal)
            session.add(orm_obj)
            session.commit()
            session.refresh(orm_obj)
            return self._to_domain_goal(orm_obj)

    def update_goal(self, goal: FinancialGoal) -> None:
        if goal.id is None:
            raise ValueError("Goal id is required for update")
        with self._provider.get_session() as session:
            orm_obj = session.query(ORMFinancialGoal).filter_by(id=goal.id).first()
            if orm_obj:
                orm_obj.name = goal.name
                orm_obj.target_amount = goal.target_amount
                orm_obj.current_amount = goal.current_amount
                orm_obj.deadline = goal.deadline
                orm_obj.priority = goal.priority
                orm_obj.status = goal.status
                session.commit()

    def delete_goal(self, goal_id: int) -> None:
        with self._provider.get_session() as session:
            orm_obj = session.query(ORMFinancialGoal).filter_by(id=goal_id).first()
            if orm_obj:
                session.delete(orm_obj)
                session.commit()

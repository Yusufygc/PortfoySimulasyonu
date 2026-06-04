# src/infrastructure/db/sqlalchemy/repositories/sa_planning_repository.py

from datetime import date
from decimal import Decimal
from typing import List, Optional
from src.domain.models.budget import Budget, BudgetItem, BudgetPinnedItem
from src.domain.models.financial_goal import FinancialGoal
from src.domain.ports.repositories.i_planning_repo import IPlanningRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMBudget, ORMBudgetItem, ORMBudgetPinnedItem, ORMFinancialGoal
from src.infrastructure.db.sqlalchemy.repositories._transaction import commit_or_rollback, commit_refresh_or_rollback

class SQLAlchemyPlanningRepository(IPlanningRepository):
    """
    IPlanningRepository arayüzünün SQLAlchemy tabanlı uygulaması.
    """

    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider
        ORMBudget.__table__.create(bind=self._provider._engine, checkfirst=True)
        ORMBudgetItem.__table__.create(bind=self._provider._engine, checkfirst=True)
        ORMBudgetPinnedItem.__table__.create(bind=self._provider._engine, checkfirst=True)
        ORMFinancialGoal.__table__.create(bind=self._provider._engine, checkfirst=True)

    # ==================== Row → Domain Mappers ==================== #
    def _to_domain_budget(self, orm: ORMBudget) -> Budget:
        items = [
            BudgetItem(
                id=i.id,
                budget_id=i.budget_id,
                item_type=i.item_type,
                name=i.name,
                amount=Decimal(str(i.amount)),
            )
            for i in orm.items
        ]
        return Budget(
            id=orm.id,
            month=orm.month,
            savings_target=Decimal(str(orm.savings_target)),
            items=items,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def _to_domain_pinned_item(self, orm: ORMBudgetPinnedItem) -> BudgetPinnedItem:
        return BudgetPinnedItem(
            id=orm.id,
            item_type=orm.item_type,
            name=orm.name,
            default_amount=Decimal(str(orm.default_amount)),
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def _to_domain_goal(self, orm: ORMFinancialGoal) -> FinancialGoal:
        return FinancialGoal(
            id=orm.id,
            name=orm.name,
            target_amount=Decimal(str(orm.target_amount)),
            current_amount=Decimal(str(orm.current_amount)),
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
            orm_obj = session.query(ORMBudget).filter_by(month=budget.month).first()
            if orm_obj is None:
                orm_obj = ORMBudget(month=budget.month, savings_target=budget.savings_target)
                session.add(orm_obj)
                session.flush()  # id üret
            else:
                orm_obj.savings_target = budget.savings_target

            # Tüm mevcut kalemleri sil, yeniden yaz
            session.query(ORMBudgetItem).filter_by(budget_id=orm_obj.id).delete()
            for item in budget.items:
                session.add(ORMBudgetItem(
                    budget_id=orm_obj.id,
                    item_type=item.item_type,
                    name=item.name,
                    amount=item.amount,
                ))

            commit_or_rollback(session)
            session.refresh(orm_obj)
            return self._to_domain_budget(orm_obj)

    def delete_budget(self, budget_id: int) -> None:
        with self._provider.get_session() as session:
            orm_obj = session.query(ORMBudget).filter_by(id=budget_id).first()
            if orm_obj:
                session.delete(orm_obj)
                commit_or_rollback(session)

    def get_pinned_budget_items(self) -> List[BudgetPinnedItem]:
        with self._provider.get_session() as session:
            rows = (
                session.query(ORMBudgetPinnedItem)
                .order_by(ORMBudgetPinnedItem.item_type.asc(), ORMBudgetPinnedItem.name.asc())
                .all()
            )
            return [self._to_domain_pinned_item(row) for row in rows]

    def upsert_pinned_budget_item(self, item: BudgetPinnedItem) -> BudgetPinnedItem:
        with self._provider.get_session() as session:
            orm_obj = (
                session.query(ORMBudgetPinnedItem)
                .filter_by(item_type=item.item_type, name=item.name)
                .first()
            )
            if orm_obj is None:
                orm_obj = ORMBudgetPinnedItem(
                    item_type=item.item_type,
                    name=item.name,
                    default_amount=item.default_amount,
                )
                session.add(orm_obj)
                session.flush()
            else:
                orm_obj.default_amount = item.default_amount

            commit_or_rollback(session)
            session.refresh(orm_obj)
            return self._to_domain_pinned_item(orm_obj)

    def delete_pinned_budget_item(self, item_type: str, name: str) -> None:
        with self._provider.get_session() as session:
            orm_obj = (
                session.query(ORMBudgetPinnedItem)
                .filter_by(item_type=item_type, name=name.strip())
                .first()
            )
            if orm_obj:
                session.delete(orm_obj)
                commit_or_rollback(session)

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
            commit_refresh_or_rollback(session, orm_obj)
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
                commit_or_rollback(session)

    def delete_goal(self, goal_id: int) -> None:
        with self._provider.get_session() as session:
            orm_obj = session.query(ORMFinancialGoal).filter_by(id=goal_id).first()
            if orm_obj:
                session.delete(orm_obj)
                commit_or_rollback(session)

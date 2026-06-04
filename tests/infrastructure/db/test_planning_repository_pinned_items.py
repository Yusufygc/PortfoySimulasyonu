from contextlib import contextmanager
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.domain.models.budget import BudgetPinnedItem
from src.infrastructure.db.sqlalchemy.repositories.sa_planning_repository import SQLAlchemyPlanningRepository


class InMemoryProvider:
    def __init__(self):
        self._engine = create_engine("sqlite:///:memory:")
        self._session_factory = sessionmaker(bind=self._engine)

    @contextmanager
    def get_session(self):
        session = self._session_factory()
        try:
            yield session
        finally:
            session.close()


def test_planning_repository_pinned_item_crud_flow():
    repo = SQLAlchemyPlanningRepository(InMemoryProvider())

    saved = repo.upsert_pinned_budget_item(
        BudgetPinnedItem(id=None, item_type="income", name="Salary", default_amount=Decimal("3000.00"))
    )
    updated = repo.upsert_pinned_budget_item(
        BudgetPinnedItem(id=None, item_type="income", name="Salary", default_amount=Decimal("3250.00"))
    )

    items = repo.get_pinned_budget_items()

    assert saved.id == updated.id
    assert len(items) == 1
    assert items[0].item_type == "income"
    assert items[0].name == "Salary"
    assert items[0].default_amount == Decimal("3250.00")

    repo.delete_pinned_budget_item("income", "Salary")

    assert repo.get_pinned_budget_items() == []

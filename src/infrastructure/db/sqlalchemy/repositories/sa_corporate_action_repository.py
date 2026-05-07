# src/infrastructure/db/sqlalchemy/repositories/sa_corporate_action_repository.py

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from src.domain.models.corporate_action import ActionType, CorporateAction
from src.domain.ports.repositories.i_corporate_action_repo import ICorporateActionRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMCorporateAction


class SQLAlchemyCorporateActionRepository(ICorporateActionRepository):

    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    # ──────────────── Mapper ────────────────

    def _to_domain(self, orm: ORMCorporateAction) -> CorporateAction:
        return CorporateAction(
            id=orm.id,
            stock_id=orm.stock_id,
            action_type=ActionType(orm.action_type.value),
            ex_date=orm.ex_date,
            ratio=Decimal(str(orm.ratio)),
            subscription_price=Decimal(str(orm.subscription_price)) if orm.subscription_price is not None else None,
            announcement_date=orm.announcement_date,
            notes=orm.notes,
            applied=bool(orm.applied),
        )

    def _to_orm(self, domain: CorporateAction) -> ORMCorporateAction:
        return ORMCorporateAction(
            id=domain.id,
            stock_id=domain.stock_id,
            action_type=domain.action_type.value,
            ex_date=domain.ex_date,
            ratio=domain.ratio,
            subscription_price=domain.subscription_price,
            announcement_date=domain.announcement_date,
            notes=domain.notes,
            applied=domain.applied,
        )

    # ──────────────── READ ────────────────

    def get_by_id(self, action_id: int) -> Optional[CorporateAction]:
        with self._provider.get_session() as session:
            row = session.query(ORMCorporateAction).filter_by(id=action_id).first()
            return self._to_domain(row) if row else None

    def get_all(self) -> List[CorporateAction]:
        with self._provider.get_session() as session:
            rows = (
                session.query(ORMCorporateAction)
                .order_by(ORMCorporateAction.ex_date.desc(), ORMCorporateAction.id.desc())
                .all()
            )
            return [self._to_domain(r) for r in rows]

    def get_by_stock(self, stock_id: int) -> List[CorporateAction]:
        with self._provider.get_session() as session:
            rows = (
                session.query(ORMCorporateAction)
                .filter_by(stock_id=stock_id)
                .order_by(ORMCorporateAction.ex_date.desc())
                .all()
            )
            return [self._to_domain(r) for r in rows]

    def get_pending_by_stock(self, stock_id: int) -> List[CorporateAction]:
        with self._provider.get_session() as session:
            rows = (
                session.query(ORMCorporateAction)
                .filter_by(stock_id=stock_id, applied=False)
                .order_by(ORMCorporateAction.ex_date.asc())
                .all()
            )
            return [self._to_domain(r) for r in rows]

    def get_all_pending(self) -> List[CorporateAction]:
        with self._provider.get_session() as session:
            rows = (
                session.query(ORMCorporateAction)
                .filter_by(applied=False)
                .order_by(ORMCorporateAction.ex_date.asc())
                .all()
            )
            return [self._to_domain(r) for r in rows]

    # ──────────────── WRITE ────────────────

    def insert(self, action: CorporateAction) -> CorporateAction:
        with self._provider.get_session() as session:
            orm_obj = self._to_orm(action)
            orm_obj.id = None
            session.add(orm_obj)
            session.commit()
            session.refresh(orm_obj)
            return self._to_domain(orm_obj)

    def mark_applied(self, action_id: int) -> None:
        with self._provider.get_session() as session:
            row = session.query(ORMCorporateAction).filter_by(id=action_id).first()
            if row:
                row.applied = True
                row.applied_at = datetime.now()
                session.commit()

    def delete(self, action_id: int) -> None:
        with self._provider.get_session() as session:
            row = session.query(ORMCorporateAction).filter_by(id=action_id).first()
            if row:
                session.delete(row)
                session.commit()

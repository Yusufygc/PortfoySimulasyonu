from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Iterable, List, Optional

from src.domain.models.cash_movement import CashMovement, CashMovementType
from src.domain.ports.repositories.i_cash_movement_repo import ICashMovementRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMCashMovement
from src.infrastructure.db.sqlalchemy.repositories._transaction import commit_or_rollback, commit_refresh_or_rollback


class SQLAlchemyCashMovementRepository(ICashMovementRepository):
    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider
        ORMCashMovement.__table__.create(bind=self._provider._engine, checkfirst=True)

    def _to_domain(self, orm: ORMCashMovement) -> CashMovement:
        amount = orm.amount
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        return CashMovement(
            id=orm.id,
            movement_date=orm.movement_date,
            movement_time=orm.movement_time,
            type=CashMovementType(orm.type.value),
            amount=amount,
            notes=orm.notes,
            created_at=orm.created_at,
        )

    @staticmethod
    def _to_orm(domain: CashMovement) -> ORMCashMovement:
        return ORMCashMovement(
            id=domain.id,
            movement_date=domain.movement_date,
            movement_time=domain.movement_time,
            type=domain.type.value,
            amount=domain.amount,
            notes=domain.notes,
        )

    def get_all_movements(self) -> List[CashMovement]:
        with self._provider.get_session() as session:
            rows = (
                session.query(ORMCashMovement)
                .order_by(ORMCashMovement.movement_date, ORMCashMovement.movement_time, ORMCashMovement.id)
                .all()
            )
            return [self._to_domain(row) for row in rows]

    def get_movements_until(
        self,
        movement_date: date,
        movement_time: Optional[time] = None,
    ) -> List[CashMovement]:
        with self._provider.get_session() as session:
            query = session.query(ORMCashMovement).filter(ORMCashMovement.movement_date <= movement_date)
            rows = query.order_by(
                ORMCashMovement.movement_date,
                ORMCashMovement.movement_time,
                ORMCashMovement.id,
            ).all()
            if movement_time is None:
                return [self._to_domain(row) for row in rows]
            return [
                self._to_domain(row)
                for row in rows
                if row.movement_date < movement_date or row.movement_time is None or row.movement_time <= movement_time
            ]

    def insert_movement(self, movement: CashMovement) -> CashMovement:
        with self._provider.get_session() as session:
            orm_obj = self._to_orm(movement)
            session.add(orm_obj)
            commit_refresh_or_rollback(session, orm_obj)
            return self._to_domain(orm_obj)

    def insert_movements_bulk(self, movements: Iterable[CashMovement]) -> None:
        movement_list = list(movements)
        if not movement_list:
            return
        with self._provider.get_session() as session:
            session.add_all([self._to_orm(movement) for movement in movement_list])
            commit_or_rollback(session)

    def delete_all_movements(self) -> None:
        with self._provider.get_session() as session:
            session.query(ORMCashMovement).delete()
            commit_or_rollback(session)

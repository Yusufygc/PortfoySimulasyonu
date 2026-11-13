from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from src.domain.models.fx_conversion import FxConversion, FxSide
from src.domain.ports.repositories.i_fx_conversion_repo import IFxConversionRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMFxConversion
from src.infrastructure.db.sqlalchemy.repositories._transaction import commit_refresh_or_rollback, commit_or_rollback


def _decimal(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _to_domain(orm: ORMFxConversion) -> FxConversion:
    return FxConversion(
        id=orm.id,
        conversion_date=orm.conversion_date,
        conversion_time=orm.conversion_time,
        side=FxSide(orm.side),
        usd_amount=_decimal(orm.usd_amount),
        rate=_decimal(orm.rate),
        fee_try=_decimal(orm.fee_try),
        note=orm.note,
    )


class SQLAlchemyFxConversionRepository(IFxConversionRepository):
    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    def add(self, conversion: FxConversion) -> FxConversion:
        with self._provider.get_session() as session:
            orm = ORMFxConversion(
                conversion_date=conversion.conversion_date,
                conversion_time=conversion.conversion_time,
                side=conversion.side.value,
                usd_amount=conversion.usd_amount,
                rate=conversion.rate,
                fee_try=conversion.fee_try,
                note=conversion.note,
            )
            session.add(orm)
            commit_refresh_or_rollback(session, orm)
            return _to_domain(orm)

    def get(self, conversion_id: int) -> Optional[FxConversion]:
        with self._provider.get_session() as session:
            orm = session.get(ORMFxConversion, conversion_id)
            return _to_domain(orm) if orm else None

    def list_all(self) -> List[FxConversion]:
        with self._provider.get_session() as session:
            rows = (
                session.query(ORMFxConversion)
                .order_by(ORMFxConversion.conversion_date, ORMFxConversion.conversion_time, ORMFxConversion.id)
                .all()
            )
            return [_to_domain(row) for row in rows]

    def delete(self, conversion_id: int) -> None:
        with self._provider.get_session() as session:
            orm = session.get(ORMFxConversion, conversion_id)
            if orm is not None:
                session.delete(orm)
                commit_or_rollback(session)

    def delete_all(self) -> None:
        with self._provider.get_session() as session:
            session.query(ORMFxConversion).delete()
            commit_or_rollback(session)

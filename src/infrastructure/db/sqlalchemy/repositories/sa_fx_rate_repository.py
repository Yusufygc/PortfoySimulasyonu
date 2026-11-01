from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterable, List, Optional

from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.domain.models.asset_price import FxRate
from src.domain.ports.repositories.i_fx_rate_repo import IFxRateRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMFxRate
from src.infrastructure.db.sqlalchemy.repositories._transaction import commit_or_rollback


def _to_domain(orm: ORMFxRate) -> FxRate:
    rate = orm.rate if isinstance(orm.rate, Decimal) else Decimal(str(orm.rate))
    return FxRate(
        id=orm.id,
        base_currency=orm.base_currency,
        quote_currency=orm.quote_currency,
        rate_date=orm.rate_date,
        rate=rate,
        source=orm.source,
    )


class SQLAlchemyFxRateRepository(IFxRateRepository):
    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    def upsert_rates(self, rates: Iterable[FxRate]) -> None:
        rows = [
            {
                "base_currency": r.base_currency,
                "quote_currency": r.quote_currency,
                "rate_date": r.rate_date,
                "rate": r.rate,
                "source": r.source,
            }
            for r in rates
        ]
        if not rows:
            return
        with self._provider.get_session() as session:
            for start in range(0, len(rows), 500):
                stmt = sqlite_insert(ORMFxRate).values(rows[start:start + 500])
                stmt = stmt.on_conflict_do_update(
                    index_elements=["base_currency", "quote_currency", "rate_date"],
                    set_={"rate": stmt.excluded.rate, "source": stmt.excluded.source},
                )
                session.execute(stmt)
            commit_or_rollback(session)

    def get_rates(
        self, base_currency: str, quote_currency: str, start: Optional[date] = None, end: Optional[date] = None
    ) -> List[FxRate]:
        with self._provider.get_session() as session:
            query = session.query(ORMFxRate).filter(
                ORMFxRate.base_currency == base_currency.upper(),
                ORMFxRate.quote_currency == quote_currency.upper(),
            )
            if start is not None:
                query = query.filter(ORMFxRate.rate_date >= start)
            if end is not None:
                query = query.filter(ORMFxRate.rate_date <= end)
            return [_to_domain(row) for row in query.order_by(ORMFxRate.rate_date).all()]

    def get_rate_on_or_before(self, base_currency: str, quote_currency: str, on_date: date) -> Optional[FxRate]:
        with self._provider.get_session() as session:
            row = (
                session.query(ORMFxRate)
                .filter(
                    ORMFxRate.base_currency == base_currency.upper(),
                    ORMFxRate.quote_currency == quote_currency.upper(),
                    ORMFxRate.rate_date <= on_date,
                )
                .order_by(ORMFxRate.rate_date.desc())
                .first()
            )
            return _to_domain(row) if row is not None else None

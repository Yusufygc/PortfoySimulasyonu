"""Golden Cross olay SQLAlchemy repository."""
from __future__ import annotations

from datetime import date
from typing import Iterable, List, Optional

from sqlalchemy.dialects.mysql import insert

from src.domain.models.golden_cross_event import CrossType, GoldenCrossEvent
from src.domain.ports.repositories.i_golden_cross_repo import IGoldenCrossRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import (
    CrossTypeEnum,
    ORMGoldenCrossEvent,
    ORMStock,
)
from src.infrastructure.db.sqlalchemy.repositories._transaction import commit_or_rollback


class SQLAlchemyGoldenCrossRepository(IGoldenCrossRepository):
    """Golden / Death Cross olayları için MySQL repo (INSERT IGNORE ile idempotent)."""

    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    # ------------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------------

    def upsert_events_bulk(self, events: Iterable[GoldenCrossEvent]) -> int:
        rows = [self._to_row(e) for e in events]
        if not rows:
            return 0
        with self._provider.get_session() as session:
            stmt = insert(ORMGoldenCrossEvent).values(rows)
            # Duplicate (stock_id, cross_date, cross_type) → no-op (mevcut korunur)
            stmt = stmt.on_duplicate_key_update(close_price=stmt.inserted.close_price)
            result = session.execute(stmt)
            commit_or_rollback(session)
            return int(result.rowcount or 0)

    def delete_all(self) -> int:
        with self._provider.get_session() as session:
            n = session.query(ORMGoldenCrossEvent).delete()
            commit_or_rollback(session)
            return int(n)

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def get_recent_events(
        self,
        since: date,
        cross_type: Optional[CrossType] = None,
        limit: int = 200,
    ) -> List[GoldenCrossEvent]:
        with self._provider.get_session() as session:
            q = (
                session.query(ORMGoldenCrossEvent, ORMStock.ticker)
                .join(ORMStock, ORMStock.id == ORMGoldenCrossEvent.stock_id)
                .filter(ORMGoldenCrossEvent.cross_date >= since)
            )
            if cross_type is not None:
                q = q.filter(ORMGoldenCrossEvent.cross_type == CrossTypeEnum(cross_type.value))
            rows = q.order_by(ORMGoldenCrossEvent.cross_date.desc()).limit(limit).all()
            return [self._to_domain(row, ticker) for row, ticker in rows]

    def get_events_for_stock(self, stock_id: int) -> List[GoldenCrossEvent]:
        with self._provider.get_session() as session:
            stock = session.query(ORMStock).filter_by(id=stock_id).first()
            ticker = stock.ticker if stock else ""
            rows = (
                session.query(ORMGoldenCrossEvent)
                .filter_by(stock_id=stock_id)
                .order_by(ORMGoldenCrossEvent.cross_date.desc())
                .all()
            )
            return [self._to_domain(r, ticker) for r in rows]

    def get_last_cross_date_for_stock(self, stock_id: int) -> Optional[date]:
        with self._provider.get_session() as session:
            row = (
                session.query(ORMGoldenCrossEvent.cross_date)
                .filter_by(stock_id=stock_id)
                .order_by(ORMGoldenCrossEvent.cross_date.desc())
                .first()
            )
            return row[0] if row else None

    # ------------------------------------------------------------------
    # Mappers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_row(e: GoldenCrossEvent) -> dict:
        return {
            "stock_id":    e.stock_id,
            "cross_date":  e.cross_date,
            "cross_type":  CrossTypeEnum(e.cross_type.value),
            "short_ma":    e.short_ma,
            "long_ma":     e.long_ma,
            "close_price": e.close_price,
        }

    @staticmethod
    def _to_domain(orm: ORMGoldenCrossEvent, ticker: str) -> GoldenCrossEvent:
        return GoldenCrossEvent(
            id=orm.id,
            stock_id=orm.stock_id,
            ticker=ticker,
            cross_date=orm.cross_date,
            cross_type=CrossType(orm.cross_type.value if hasattr(orm.cross_type, "value") else orm.cross_type),
            short_ma=orm.short_ma,
            long_ma=orm.long_ma,
            close_price=orm.close_price,
            detected_at=orm.detected_at,
        )

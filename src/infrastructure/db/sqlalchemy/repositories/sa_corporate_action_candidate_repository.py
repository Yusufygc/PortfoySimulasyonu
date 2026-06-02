from __future__ import annotations

from decimal import Decimal
from typing import Iterable, List, Optional, Sequence

from src.domain.models.corporate_action import ActionType
from src.domain.models.corporate_action_candidate import (
    CorporateActionCandidate,
    CorporateActionCandidateStatus,
)
from src.domain.ports.repositories.i_corporate_action_candidate_repo import (
    ICorporateActionCandidateRepository,
)
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMCorporateActionCandidate
from src.infrastructure.db.sqlalchemy.repositories._transaction import commit_or_rollback, commit_refresh_or_rollback


class SQLAlchemyCorporateActionCandidateRepository(ICorporateActionCandidateRepository):
    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    def _to_domain(self, orm: ORMCorporateActionCandidate) -> CorporateActionCandidate:
        return CorporateActionCandidate(
            id=orm.id,
            ticker=orm.ticker,
            stock_id=orm.stock_id,
            source=orm.source,
            source_disclosure_id=orm.source_disclosure_id,
            source_url=orm.source_url,
            action_type=ActionType(orm.action_type.value),
            status=CorporateActionCandidateStatus(orm.status),
            ratio=Decimal(str(orm.ratio)) if orm.ratio is not None else None,
            subscription_price=(
                Decimal(str(orm.subscription_price)) if orm.subscription_price is not None else None
            ),
            announcement_date=orm.announcement_date,
            ex_date=orm.ex_date,
            confidence=Decimal(str(orm.confidence or 0)),
            raw_payload_json=orm.raw_payload_json,
            parse_notes=orm.parse_notes,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def _to_orm(self, candidate: CorporateActionCandidate) -> ORMCorporateActionCandidate:
        return ORMCorporateActionCandidate(
            id=candidate.id,
            ticker=candidate.ticker,
            stock_id=candidate.stock_id,
            source=candidate.source,
            source_disclosure_id=candidate.source_disclosure_id,
            source_url=candidate.source_url,
            action_type=candidate.action_type.value,
            status=candidate.status.value,
            ratio=candidate.ratio,
            subscription_price=candidate.subscription_price,
            announcement_date=candidate.announcement_date,
            ex_date=candidate.ex_date,
            confidence=candidate.confidence,
            raw_payload_json=candidate.raw_payload_json,
            parse_notes=candidate.parse_notes,
        )

    def get_by_id(self, candidate_id: int) -> Optional[CorporateActionCandidate]:
        with self._provider.get_session() as session:
            row = session.query(ORMCorporateActionCandidate).filter_by(id=candidate_id).first()
            return self._to_domain(row) if row else None

    def get_by_statuses(
        self,
        statuses: Sequence[CorporateActionCandidateStatus],
    ) -> List[CorporateActionCandidate]:
        status_values = [status.value for status in statuses]
        if not status_values:
            return []
        with self._provider.get_session() as session:
            rows = (
                session.query(ORMCorporateActionCandidate)
                .filter(ORMCorporateActionCandidate.status.in_(status_values))
                .order_by(
                    ORMCorporateActionCandidate.ex_date.asc(),
                    ORMCorporateActionCandidate.ticker.asc(),
                )
                .all()
            )
            return [self._to_domain(row) for row in rows]

    def find_duplicate(self, candidate: CorporateActionCandidate) -> Optional[CorporateActionCandidate]:
        with self._provider.get_session() as session:
            row = self._duplicate_query(session, candidate).first()
            return self._to_domain(row) if row else None

    def upsert_discovered(
        self,
        candidates: Iterable[CorporateActionCandidate],
    ) -> List[CorporateActionCandidate]:
        saved: list[CorporateActionCandidate] = []
        with self._provider.get_session() as session:
            for candidate in candidates:
                row = self._duplicate_query(session, candidate).first()
                if row is None:
                    row = self._to_orm(candidate)
                    row.id = None
                    session.add(row)
                elif row.status not in (
                    CorporateActionCandidateStatus.APPLIED.value,
                    CorporateActionCandidateStatus.IGNORED.value,
                ):
                    self._copy_to_row(row, candidate)
                saved.append(row)
            commit_or_rollback(session)
            for row in saved:
                session.refresh(row)
            return [self._to_domain(row) for row in saved]

    def update(self, candidate: CorporateActionCandidate) -> CorporateActionCandidate:
        if candidate.id is None:
            raise ValueError("Candidate id is required for update")
        with self._provider.get_session() as session:
            row = session.query(ORMCorporateActionCandidate).filter_by(id=candidate.id).first()
            if row is None:
                raise ValueError(f"Candidate not found: id={candidate.id}")
            self._copy_to_row(row, candidate)
            commit_refresh_or_rollback(session, row)
            return self._to_domain(row)

    def update_status(
        self,
        candidate_id: int,
        status: CorporateActionCandidateStatus,
    ) -> None:
        with self._provider.get_session() as session:
            row = session.query(ORMCorporateActionCandidate).filter_by(id=candidate_id).first()
            if row:
                row.status = status.value
                commit_or_rollback(session)

    def _duplicate_query(self, session, candidate: CorporateActionCandidate):
        return session.query(ORMCorporateActionCandidate).filter_by(
            source=candidate.source,
            source_disclosure_id=candidate.source_disclosure_id,
            action_type=candidate.action_type.value,
            ticker=candidate.ticker,
        )

    def _copy_to_row(
        self,
        row: ORMCorporateActionCandidate,
        candidate: CorporateActionCandidate,
    ) -> None:
        row.ticker = candidate.ticker
        row.stock_id = candidate.stock_id
        row.source = candidate.source
        row.source_disclosure_id = candidate.source_disclosure_id
        row.source_url = candidate.source_url
        row.action_type = candidate.action_type.value
        row.status = candidate.status.value
        row.ratio = candidate.ratio
        row.subscription_price = candidate.subscription_price
        row.announcement_date = candidate.announcement_date
        row.ex_date = candidate.ex_date
        row.confidence = candidate.confidence
        row.raw_payload_json = candidate.raw_payload_json
        row.parse_notes = candidate.parse_notes

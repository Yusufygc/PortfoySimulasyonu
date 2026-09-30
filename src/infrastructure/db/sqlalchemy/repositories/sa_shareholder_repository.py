"""KAP pay sahipliği SQLAlchemy repository."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from src.domain.models.shareholder import ShareholderRow, ShareholderSnapshot
from src.domain.ports.repositories.i_shareholder_repo import IShareholderRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import (
    ORMKapCompany,
    ORMKapShareholderRow,
    ORMKapShareholderSnapshot,
)
from src.infrastructure.db.sqlalchemy.repositories._transaction import commit_or_rollback


class SQLAlchemyKapShareholderRepository(IShareholderRepository):
    """KAP ortaklık yapısı kalıcı katmanı."""

    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    # ------------------------------------------------------------------
    # Companies
    # ------------------------------------------------------------------

    def upsert_company(self, ticker: str, mkk_member_oid: str, title: Optional[str]) -> int:
        from sqlalchemy import func
        ticker = ticker.strip().upper()
        with self._provider.get_session() as session:
            row = session.query(ORMKapCompany).filter_by(ticker=ticker).first()
            if row is None:
                max_id = session.query(func.max(ORMKapCompany.id)).scalar() or 0
                row = ORMKapCompany(
                    id=max_id + 1,
                    ticker=ticker,
                    mkk_member_oid=mkk_member_oid,
                    title=title,
                )
                session.add(row)
            else:
                row.mkk_member_oid = mkk_member_oid
                if title:
                    row.title = title
            commit_or_rollback(session)
            session.refresh(row)
            return int(row.id)

    def get_mkk_oid(self, ticker: str) -> Optional[str]:
        ticker = ticker.strip().upper()
        with self._provider.get_session() as session:
            row = session.query(ORMKapCompany).filter_by(ticker=ticker).first()
            return row.mkk_member_oid if row else None

    def get_last_fetched_at(self, ticker: str) -> Optional[datetime]:
        ticker = ticker.strip().upper()
        with self._provider.get_session() as session:
            row = session.query(ORMKapCompany).filter_by(ticker=ticker).first()
            return row.last_fetched_at if row else None

    # ------------------------------------------------------------------
    # Snapshots — replace = atomik tarihçe değiştirme
    # ------------------------------------------------------------------

    def replace_shareholder_history(
        self,
        ticker: str,
        snapshots: list[ShareholderSnapshot],
    ) -> None:
        from sqlalchemy import func
        ticker = ticker.strip().upper()
        with self._provider.get_session() as session:
            company = session.query(ORMKapCompany).filter_by(ticker=ticker).first()
            if company is None:
                raise ValueError(f"{ticker}: kap_companies'te kayıt yok (önce upsert_company)")

            session.query(ORMKapShareholderSnapshot).filter_by(company_id=company.id).delete()

            snap_max_id = session.query(func.max(ORMKapShareholderSnapshot.id)).scalar() or 0
            row_max_id = session.query(func.max(ORMKapShareholderRow.id)).scalar() or 0

            for snap in snapshots:
                snap_max_id += 1
                orm_snap = ORMKapShareholderSnapshot(
                    id=snap_max_id,
                    company_id=company.id,
                    creation_date=snap.creation_date,
                )
                session.add(orm_snap)
                for r in snap.rows:
                    row_max_id += 1
                    session.add(ORMKapShareholderRow(
                        id=row_max_id,
                        snapshot_id=orm_snap.id,
                        shareholder_name=r.shareholder_name[:500],
                        share_in_capital=r.share_in_capital,
                        ratio_in_capital=r.ratio_in_capital,
                        voting_right_ratio=r.voting_right_ratio,
                        is_total=r.is_total,
                    ))
            company.last_fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)
            commit_or_rollback(session)

    def get_shareholder_history(self, ticker: str) -> list[ShareholderSnapshot]:
        ticker = ticker.strip().upper()
        with self._provider.get_session() as session:
            company = session.query(ORMKapCompany).filter_by(ticker=ticker).first()
            if company is None:
                return []
            snap_rows = (
                session.query(ORMKapShareholderSnapshot)
                .filter_by(company_id=company.id)
                .order_by(ORMKapShareholderSnapshot.creation_date.desc())
                .all()
            )
            out: list[ShareholderSnapshot] = []
            for snap in snap_rows:
                domain_rows = tuple(
                    ShareholderRow(
                        shareholder_name=r.shareholder_name,
                        share_in_capital=r.share_in_capital,
                        ratio_in_capital=r.ratio_in_capital,
                        voting_right_ratio=r.voting_right_ratio,
                        is_total=bool(r.is_total),
                    )
                    for r in snap.rows
                )
                out.append(ShareholderSnapshot(
                    creation_date=snap.creation_date,
                    rows=domain_rows,
                ))
            return out

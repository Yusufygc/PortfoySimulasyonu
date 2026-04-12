# src/infrastructure/db/sqlalchemy/repositories/sa_risk_profile_repository.py

from typing import List, Optional
from src.domain.models.risk_profile import RiskProfile
from src.domain.ports.repositories.i_risk_profile_repo import IRiskProfileRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMRiskProfile

class SQLAlchemyRiskProfileRepository(IRiskProfileRepository):
    """
    IRiskProfileRepository arayüzünün SQLAlchemy tabanlı uygulaması.
    """

    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    def _to_domain(self, orm: ORMRiskProfile) -> RiskProfile:
        return RiskProfile(
            id=orm.id,
            age=int(orm.age or 0),
            horizon=orm.horizon or "medium",
            reaction=orm.reaction or "hold",
            risk_score=int(orm.risk_score or 0),
            risk_label=orm.risk_label or "DENGELİ",
            created_at=orm.created_at,
        )

    def _to_orm(self, domain: RiskProfile) -> ORMRiskProfile:
        return ORMRiskProfile(
            id=domain.id,
            age=domain.age,
            horizon=domain.horizon,
            reaction=domain.reaction,
            risk_score=domain.risk_score,
            risk_label=domain.risk_label
        )

    def get_latest_profile(self) -> Optional[RiskProfile]:
        with self._provider.get_session() as session:
            row = session.query(ORMRiskProfile).order_by(ORMRiskProfile.id.desc()).first()
            return self._to_domain(row) if row else None

    def save_profile(self, profile: RiskProfile) -> RiskProfile:
        with self._provider.get_session() as session:
            orm_obj = self._to_orm(profile)
            session.add(orm_obj)
            session.commit()
            session.refresh(orm_obj)
            return self._to_domain(orm_obj)

    def get_all_profiles(self) -> List[RiskProfile]:
        with self._provider.get_session() as session:
            rows = session.query(ORMRiskProfile).order_by(ORMRiskProfile.id.desc()).all()
            return [self._to_domain(r) for r in rows]

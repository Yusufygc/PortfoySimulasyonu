# src/infrastructure/db/sqlalchemy/repositories/sa_risk_profile_repository.py

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from src.domain.models.risk_profile import PROFILE_INFO, RiskLabel, RiskProfile
from src.domain.ports.repositories.i_risk_profile_repo import IRiskProfileRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMRiskProfile


class SQLAlchemyRiskProfileRepository(IRiskProfileRepository):
    """IRiskProfileRepository arayuzunun SQLAlchemy tabanli uygulamasi."""

    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    def _to_domain(self, orm: ORMRiskProfile) -> RiskProfile:
        label = self._normalize_label(orm.risk_label)
        allocation = self._json_dict(getattr(orm, "recommended_allocation_json", None))
        if not allocation:
            allocation = dict(PROFILE_INFO.get(label, PROFILE_INFO[RiskLabel.DENGELI])["allocation"])

        return RiskProfile(
            id=orm.id,
            age=int(orm.age or 0),
            horizon=orm.horizon or "medium",
            reaction=orm.reaction or "hold",
            risk_score=int(orm.risk_score or 0),
            risk_label=label,
            questionnaire_version=getattr(orm, "questionnaire_version", None) or "legacy",
            answers=self._json_dict(getattr(orm, "answers_json", None)),
            dimension_scores={k: int(v) for k, v in self._json_dict(getattr(orm, "dimension_scores_json", None)).items()},
            recommended_allocation={k: int(v) for k, v in allocation.items()},
            suitability_notes=self._notes_list(getattr(orm, "suitability_notes", None)),
            created_at=orm.created_at,
        )

    def _to_orm(self, domain: RiskProfile) -> ORMRiskProfile:
        return ORMRiskProfile(
            id=domain.id,
            age=domain.age,
            horizon=domain.horizon,
            reaction=domain.reaction,
            risk_score=domain.risk_score,
            risk_label=domain.risk_label,
            questionnaire_version=domain.questionnaire_version,
            answers_json=dict(domain.answers),
            dimension_scores_json=dict(domain.dimension_scores),
            recommended_allocation_json=dict(domain.recommended_allocation),
            suitability_notes="\n".join(domain.suitability_notes),
        )

    def get_latest_profile(self) -> Optional[RiskProfile]:
        with self._provider.get_session() as session:
            try:
                row = session.query(ORMRiskProfile).order_by(ORMRiskProfile.id.desc()).first()
                return self._to_domain(row) if row else None
            except ProgrammingError as exc:
                if not self._is_missing_professional_column(exc):
                    raise
                session.rollback()
                row = session.execute(
                    text(
                        "SELECT id, age, horizon, reaction, risk_score, risk_label, created_at "
                        "FROM risk_profiles ORDER BY id DESC LIMIT 1"
                    )
                ).mappings().first()
                return self._legacy_row_to_domain(row) if row else None

    def save_profile(self, profile: RiskProfile) -> RiskProfile:
        with self._provider.get_session() as session:
            try:
                orm_obj = self._to_orm(profile)
                session.add(orm_obj)
                session.commit()
                session.refresh(orm_obj)
                return self._to_domain(orm_obj)
            except ProgrammingError as exc:
                if not self._is_missing_professional_column(exc):
                    raise
                session.rollback()
                return self._save_legacy_compatible(session, profile)

    def get_all_profiles(self) -> List[RiskProfile]:
        with self._provider.get_session() as session:
            try:
                rows = session.query(ORMRiskProfile).order_by(ORMRiskProfile.id.desc()).all()
                return [self._to_domain(row) for row in rows]
            except ProgrammingError as exc:
                if not self._is_missing_professional_column(exc):
                    raise
                session.rollback()
                rows = session.execute(
                    text(
                        "SELECT id, age, horizon, reaction, risk_score, risk_label, created_at "
                        "FROM risk_profiles ORDER BY id DESC"
                    )
                ).mappings().all()
                return [self._legacy_row_to_domain(row) for row in rows]

    def _save_legacy_compatible(self, session, profile: RiskProfile) -> RiskProfile:
        result = session.execute(
            text(
                "INSERT INTO risk_profiles (age, horizon, reaction, risk_score, risk_label) "
                "VALUES (:age, :horizon, :reaction, :risk_score, :risk_label)"
            ),
            {
                "age": profile.age,
                "horizon": profile.horizon,
                "reaction": profile.reaction,
                "risk_score": profile.risk_score,
                "risk_label": profile.risk_label,
            },
        )
        session.commit()
        profile.id = int(getattr(result, "lastrowid", 0) or 0) or None
        profile.suitability_notes = list(profile.suitability_notes) + [
            "Veritabani eski semada oldugu icin detayli anket yanitlari kalici olarak saklanamadi. "
            "Kalici detaylar icin scripts/alter_risk_profile_professional.sql uygulanmalidir."
        ]
        return profile

    def _legacy_row_to_domain(self, row) -> RiskProfile:
        label = self._normalize_label(row["risk_label"])
        return RiskProfile(
            id=int(row["id"]),
            age=int(row["age"] or 0),
            horizon=row["horizon"] or "medium",
            reaction=row["reaction"] or "hold",
            risk_score=int(row["risk_score"] or 0),
            risk_label=label,
            questionnaire_version="legacy",
            recommended_allocation=dict(PROFILE_INFO.get(label, PROFILE_INFO[RiskLabel.DENGELI])["allocation"]),
            created_at=row["created_at"],
        )

    @staticmethod
    def _json_dict(value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return {}

    @staticmethod
    def _notes_list(value: Any) -> List[str]:
        if not value:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        return [line.strip() for line in str(value).splitlines() if line.strip()]

    @staticmethod
    def _normalize_label(value: Optional[str]) -> str:
        if not value:
            return RiskLabel.DENGELI
        mapping = {
            "DENGELİ": RiskLabel.DENGELI,
            "DENGELÄ°": RiskLabel.DENGELI,
            "DENGELI": RiskLabel.DENGELI,
            "MUHAFAZAKAR": RiskLabel.MUHAFAZAKAR,
            "AGRESİF": RiskLabel.AGRESIF,
            "AGRESÄ°F": RiskLabel.AGRESIF,
            "AGRESIF": RiskLabel.AGRESIF,
            "COK_MUHAFAZAKAR": RiskLabel.COK_MUHAFAZAKAR,
            "BUYUME_ODAKLI": RiskLabel.BUYUME_ODAKLI,
        }
        return mapping.get(value.upper(), RiskLabel.DENGELI)

    @staticmethod
    def _is_missing_professional_column(exc: Exception) -> bool:
        message = str(exc)
        return (
            "Unknown column" in message
            and any(
                column in message
                for column in (
                    "questionnaire_version",
                    "answers_json",
                    "dimension_scores_json",
                    "recommended_allocation_json",
                    "suitability_notes",
                )
            )
        )

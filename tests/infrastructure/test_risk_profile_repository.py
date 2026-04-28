from datetime import datetime

from sqlalchemy.exc import ProgrammingError

from src.domain.models.risk_profile import RiskLabel, RiskProfile
from src.infrastructure.db.sqlalchemy.orm_models import ORMRiskProfile
from src.infrastructure.db.sqlalchemy.repositories.sa_risk_profile_repository import SQLAlchemyRiskProfileRepository


def test_risk_profile_repository_maps_professional_json_fields():
    repo = SQLAlchemyRiskProfileRepository.__new__(SQLAlchemyRiskProfileRepository)
    orm = ORMRiskProfile(
        id=7,
        age=42,
        horizon="long",
        reaction="hold",
        risk_score=68,
        risk_label=RiskLabel.BUYUME_ODAKLI,
        questionnaire_version="professional_v1",
        answers_json={"age": "35_49"},
        dimension_scores_json={"capacity": 70, "tolerance": 65},
        recommended_allocation_json={"Nakit": 5, "Hisse": 95},
        suitability_notes="Not 1\nNot 2",
    )
    orm.created_at = datetime(2026, 4, 28)

    profile = repo._to_domain(orm)

    assert profile.id == 7
    assert profile.questionnaire_version == "professional_v1"
    assert profile.answers == {"age": "35_49"}
    assert profile.dimension_scores == {"capacity": 70, "tolerance": 65}
    assert profile.recommended_allocation == {"Nakit": 5, "Hisse": 95}
    assert profile.suitability_notes == ["Not 1", "Not 2"]


def test_risk_profile_repository_keeps_legacy_rows_readable():
    repo = SQLAlchemyRiskProfileRepository.__new__(SQLAlchemyRiskProfileRepository)
    orm = ORMRiskProfile(
        id=3,
        age=55,
        horizon="medium",
        reaction="hold",
        risk_score=50,
        risk_label="DENGELİ",
    )

    profile = repo._to_domain(orm)

    assert profile.risk_label == RiskLabel.DENGELI
    assert profile.questionnaire_version == "legacy"
    assert profile.answers == {}
    assert sum(profile.recommended_allocation.values()) == 100


def test_risk_profile_repository_serializes_domain_to_orm():
    repo = SQLAlchemyRiskProfileRepository.__new__(SQLAlchemyRiskProfileRepository)
    profile = RiskProfile(
        id=None,
        age=30,
        horizon="medium",
        reaction="hold",
        risk_score=62,
        risk_label=RiskLabel.DENGELI,
        questionnaire_version="professional_v1",
        answers={"age": "25_34"},
        dimension_scores={"capacity": 60},
        recommended_allocation={"Nakit": 10, "Hisse": 90},
        suitability_notes=["Yatirim tavsiyesi degildir."],
    )

    orm = repo._to_orm(profile)

    assert orm.answers_json == {"age": "25_34"}
    assert orm.dimension_scores_json == {"capacity": 60}
    assert orm.recommended_allocation_json == {"Nakit": 10, "Hisse": 90}
    assert orm.suitability_notes == "Yatirim tavsiyesi degildir."


def test_risk_profile_repository_detects_missing_professional_columns():
    exc = ProgrammingError(
        "INSERT INTO risk_profiles (...) VALUES (...)",
        {},
        Exception("1054 Unknown column 'questionnaire_version' in 'field list'"),
    )

    assert SQLAlchemyRiskProfileRepository._is_missing_professional_column(exc)

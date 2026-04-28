import pytest

from src.application.services.planning.risk_profile_service import RiskProfileService
from src.domain.models.risk_profile import RiskLabel


class InMemoryRiskProfileRepo:
    def __init__(self):
        self.saved = []

    def get_latest_profile(self):
        return self.saved[-1] if self.saved else None

    def save_profile(self, profile):
        profile.id = len(self.saved) + 1
        self.saved.append(profile)
        return profile

    def get_all_profiles(self):
        return list(reversed(self.saved))


def _answers_for_target(service, target_score):
    answers = {}
    for section in service.get_questionnaire():
        for question in section.questions:
            option = min(question.options, key=lambda item: abs(item.score - target_score))
            answers[question.id] = option.value
    return answers


@pytest.mark.parametrize(
    ("target_score", "expected_label"),
    [
        (0, RiskLabel.COK_MUHAFAZAKAR),
        (2, RiskLabel.MUHAFAZAKAR),
        (3, RiskLabel.DENGELI),
        (4, RiskLabel.BUYUME_ODAKLI),
        (5, RiskLabel.AGRESIF),
    ],
)
def test_professional_questionnaire_produces_all_profile_levels(target_score, expected_label):
    service = RiskProfileService(InMemoryRiskProfileRepo())

    profile = service.calculate_and_save_profile(_answers_for_target(service, target_score))

    assert profile.risk_label == expected_label
    assert 0 <= profile.risk_score <= 100
    assert set(profile.dimension_scores) == {"capacity", "tolerance", "knowledge", "goals"}
    assert sum(profile.recommended_allocation.values()) == 100


def test_consistency_checks_reduce_score_and_add_notes():
    service = RiskProfileService(InMemoryRiskProfileRepo())
    answers = _answers_for_target(service, 5)
    answers.update(
        {
            "income_stability": "unstable",
            "emergency_fund": "none",
            "debt_load": "high",
            "horizon": "short",
            "stock_experience": "none",
            "fund_bond_fx_experience": "none",
            "derivative_experience": "none",
        }
    )

    profile = service.calculate_and_save_profile(answers)

    assert profile.risk_score < 80
    assert any("finansal kapasite" in note for note in profile.suitability_notes)
    assert any("Kisa yatirim vadesi" in note for note in profile.suitability_notes)
    assert any("Bilgi/tecrube" in note for note in profile.suitability_notes)


def test_missing_or_invalid_answers_raise_value_error():
    service = RiskProfileService(InMemoryRiskProfileRepo())
    answers = _answers_for_target(service, 3)
    answers.pop("age")

    with pytest.raises(ValueError, match="Eksik anket yanitlari"):
        service.calculate_and_save_profile(answers)

    answers = _answers_for_target(service, 3)
    answers["age"] = "not-valid"

    with pytest.raises(ValueError, match="Gecersiz anket yanitlari"):
        service.calculate_and_save_profile(answers)


def test_legacy_signature_still_calculates_profile():
    service = RiskProfileService(InMemoryRiskProfileRepo())

    profile = service.calculate_and_save_profile(age=30, horizon="medium", reaction="hold")

    assert profile.questionnaire_version == "legacy"
    assert profile.risk_score == 60
    assert profile.risk_label == RiskLabel.DENGELI

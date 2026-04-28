import os
from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from src.application.services.planning.risk_profile_service import RiskProfileService
from src.domain.models.risk_profile import RiskLabel, RiskProfile
from src.ui.pages.risk_profile_page import RiskProfilePage


class DummyRepo:
    def get_latest_profile(self):
        return None

    def save_profile(self, profile):
        profile.id = 1
        return profile

    def get_all_profiles(self):
        return []


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    return app


def _page():
    service = RiskProfileService(DummyRepo())
    return RiskProfilePage(container=SimpleNamespace(risk_profile_service=service))


def test_risk_profile_page_builds_professional_questionnaire(qapp):
    page = _page()

    assert len(page.answer_groups) == 15
    assert {"age", "horizon", "loss_20", "derivative_experience"} <= set(page.answer_groups)


def test_risk_profile_page_requires_all_answers(qapp):
    page = _page()

    assert page._collect_answers() is None


def test_risk_profile_page_collects_answers_and_displays_result(qapp):
    page = _page()
    for group in page.answer_groups.values():
        group.buttons()[0].setChecked(True)

    answers = page._collect_answers()

    assert answers is not None
    assert len(answers) == 15

    profile = RiskProfile(
        id=1,
        age=30,
        horizon="medium",
        reaction="hold",
        risk_score=63,
        risk_label=RiskLabel.DENGELI,
        questionnaire_version="professional_v1",
        answers=answers,
        dimension_scores={"capacity": 60, "tolerance": 70, "knowledge": 50, "goals": 65},
        recommended_allocation={"Nakit": 10, "Tahvil/Bono": 25, "Fon": 30, "Hisse": 30, "Alternatif": 5},
        suitability_notes=["Bu sonuc yatirim tavsiyesi degildir."],
    )

    page._display_profile(profile)

    assert not page.profile_card.isHidden()
    assert "63" in page.lbl_score.text()
    assert "Dengeli" in page.lbl_label.text()
    assert page.dimension_labels["capacity"].text() == "60 / 100"
    assert "Nakit" in page.lbl_allocation.text()

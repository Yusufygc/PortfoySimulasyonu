from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from src.domain.models.corporate_action import ActionType
from src.domain.models.corporate_action_candidate import (
    CorporateActionCandidate,
    CorporateActionCandidateStatus,
)
from src.ui.pages.settings.corporate_action_candidates_panel import CorporateActionCandidatesPanel


class DummyReviewService:
    def __init__(self, candidates):
        self.candidates = candidates
        self.applied = []
        self.ignored = []

    def list_reviewable(self):
        return self.candidates

    def approve_and_apply(self, candidate_id):
        self.applied.append(candidate_id)
        return SimpleNamespace(result=SimpleNamespace(description="uygulandi"))

    def ignore(self, candidate_id):
        self.ignored.append(candidate_id)


class DummyDiscoveryService:
    def __init__(self, result=None):
        self.called = False
        self.result = result

    def discover(self):
        self.called = True
        return self.result or SimpleNamespace(saved_count=1, source_unavailable=False, errors=[])


def _candidate(status=CorporateActionCandidateStatus.READY):
    return CorporateActionCandidate(
        id=1,
        ticker="MERKO.IS",
        stock_id=47,
        source="KAP_MKK",
        source_disclosure_id="1603760",
        source_url="https://kap.org.tr/tr/Bildirim/1603760",
        action_type=ActionType.BEDELSIZ,
        status=status,
        ratio=Decimal("6.3833834"),
        subscription_price=None,
        announcement_date=None,
        ex_date=date(2026, 5, 5),
        confidence=Decimal("0.9"),
    )


def test_candidates_panel_renders_reviewable_candidate(qapp):
    review = DummyReviewService([_candidate()])
    panel = CorporateActionCandidatesPanel(
        SimpleNamespace(
            corporate_action_discovery_service=DummyDiscoveryService(),
            corporate_action_candidate_review_service=review,
            stock_repo=None,
        )
    )

    assert panel.table.rowCount() == 1
    assert panel.table.item(0, 0).text() == "MERKO.IS"
    assert panel.table.item(0, 2).text() == "READY"


def test_candidates_panel_apply_uses_review_service(qapp, monkeypatch):
    review = DummyReviewService([_candidate()])
    panel = CorporateActionCandidatesPanel(
        SimpleNamespace(
            corporate_action_discovery_service=DummyDiscoveryService(),
            corporate_action_candidate_review_service=review,
            stock_repo=None,
        )
    )
    monkeypatch.setattr("src.ui.pages.settings.corporate_action_candidates_panel.Toast.success", lambda *args: None)
    panel.table.selectRow(0)

    panel.apply_selected()

    assert review.applied == [1]


def test_candidates_panel_warns_when_discovery_source_unavailable(qapp, monkeypatch):
    warnings = []
    successes = []
    review = DummyReviewService([])
    panel = CorporateActionCandidatesPanel(
        SimpleNamespace(
            corporate_action_discovery_service=DummyDiscoveryService(
                SimpleNamespace(
                    saved_count=0,
                    source_unavailable=True,
                    errors=["KAP source 404"],
                )
            ),
            corporate_action_candidate_review_service=review,
            stock_repo=None,
        )
    )
    monkeypatch.setattr(
        "src.ui.pages.settings.corporate_action_candidates_panel.Toast.warning",
        lambda _parent, message: warnings.append(message),
    )
    monkeypatch.setattr(
        "src.ui.pages.settings.corporate_action_candidates_panel.Toast.success",
        lambda _parent, message: successes.append(message),
    )

    panel.discover()

    assert warnings
    assert "KAP source 404" in warnings[0]
    assert successes == []

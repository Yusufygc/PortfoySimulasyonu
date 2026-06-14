from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.application.services.corporate_actions.candidate_discovery_service import (
    CandidateDiscoveryDeps,
    CorporateActionDiscoveryService,
)
from src.application.services.corporate_actions.candidate_review_service import (
    CorporateActionCandidateReviewService,
)
from src.domain.models.corporate_action import ActionType, CorporateAction
from src.domain.models.corporate_action_candidate import (
    CorporateActionCandidate,
    CorporateActionCandidateStatus,
)
from src.domain.ports.services.i_corporate_action_provider import CorporateActionProviderUnavailable


class FakeCandidateRepo:
    def __init__(self):
        self.items = {}
        self.next_id = 1

    def get_by_id(self, candidate_id):
        return self.items.get(candidate_id)

    def get_by_statuses(self, statuses):
        return [candidate for candidate in self.items.values() if candidate.status in statuses]

    def find_duplicate(self, candidate):
        return next(
            (
                item
                for item in self.items.values()
                if item.source == candidate.source
                and item.source_disclosure_id == candidate.source_disclosure_id
                and item.action_type == candidate.action_type
                and item.ticker == candidate.ticker
            ),
            None,
        )

    def upsert_discovered(self, candidates):
        saved = []
        for candidate in candidates:
            duplicate = self.find_duplicate(candidate)
            if duplicate is not None:
                self.items[duplicate.id] = candidate.__class__(**{**candidate.__dict__, "id": duplicate.id})
                saved.append(self.items[duplicate.id])
                continue
            candidate = candidate.__class__(**{**candidate.__dict__, "id": self.next_id})
            self.items[self.next_id] = candidate
            self.next_id += 1
            saved.append(candidate)
        return saved

    def update(self, candidate):
        self.items[candidate.id] = candidate
        return candidate

    def update_status(self, candidate_id, status):
        self.items[candidate_id] = self.items[candidate_id].with_status(status)


class FakeProvider:
    def __init__(self, candidates):
        self.candidates = candidates
        self.calls = []

    def fetch_candidates(self, tickers, start_date=None, end_date=None):
        self.calls.append(list(tickers))
        return self.candidates


class UnavailableProvider:
    def fetch_candidates(self, tickers, start_date=None, end_date=None):
        raise CorporateActionProviderUnavailable("KAP source 404")


class FakeStockRepo:
    def __init__(self):
        self.stock = SimpleNamespace(id=47, ticker="MERKO.IS")

    def get_stock_by_ticker(self, ticker):
        return self.stock if ticker == "MERKO.IS" else None

    def get_ticker_map_for_stock_ids(self, stock_ids):
        return {47: "MERKO.IS"}


def _candidate(**overrides):
    data = dict(
        id=None,
        ticker="MERKO.IS",
        stock_id=None,
        source="KAP_MKK",
        source_disclosure_id="1603760",
        source_url="https://kap.org.tr/tr/Bildirim/1603760",
        action_type=ActionType.BEDELSIZ,
        status=CorporateActionCandidateStatus.DISCOVERED,
        ratio=Decimal("6.3833834"),
        subscription_price=None,
        announcement_date=None,
        ex_date=date(2026, 5, 5),
        confidence=Decimal("0.9"),
        raw_payload_json=None,
        parse_notes=None,
    )
    data.update(overrides)
    return CorporateActionCandidate(**data)


def test_discovery_matches_stock_and_deduplicates():
    repo = FakeCandidateRepo()
    service = CorporateActionDiscoveryService(
        deps=CandidateDiscoveryDeps(
            provider=FakeProvider([_candidate()]),
            candidate_repo=repo,
            stock_repo=FakeStockRepo(),
            action_repo=MagicMock(get_by_stock=MagicMock(return_value=[])),
            portfolio_repo=MagicMock(get_all_stock_ids_in_portfolio=MagicMock(return_value=[47])),
        ),
    )

    first = service.discover()
    second = service.discover()

    assert first.saved_count == 1
    assert second.saved_count == 1
    assert len(repo.items) == 1
    saved = next(iter(repo.items.values()))
    assert saved.stock_id == 47
    assert saved.status == CorporateActionCandidateStatus.READY


def test_discovery_skips_already_applied_action():
    action_repo = MagicMock()
    action_repo.get_by_stock.return_value = [
        CorporateAction(
            id=9,
            stock_id=47,
            action_type=ActionType.BEDELSIZ,
            ex_date=date(2026, 5, 5),
            ratio=Decimal("6.3833834"),
            subscription_price=None,
            announcement_date=None,
            notes=None,
            applied=True,
        )
    ]
    service = CorporateActionDiscoveryService(
        deps=CandidateDiscoveryDeps(
            provider=FakeProvider([_candidate()]),
            candidate_repo=FakeCandidateRepo(),
            stock_repo=FakeStockRepo(),
            action_repo=action_repo,
            portfolio_repo=MagicMock(get_all_stock_ids_in_portfolio=MagicMock(return_value=[47])),
        ),
    )

    result = service.discover()

    assert result.saved_count == 0
    assert result.skipped_applied_count == 1


def test_discovery_returns_unavailable_result_without_raising():
    service = CorporateActionDiscoveryService(
        deps=CandidateDiscoveryDeps(
            provider=UnavailableProvider(),
            candidate_repo=FakeCandidateRepo(),
            stock_repo=FakeStockRepo(),
            action_repo=MagicMock(get_by_stock=MagicMock(return_value=[])),
            portfolio_repo=MagicMock(get_all_stock_ids_in_portfolio=MagicMock(return_value=[47])),
        ),
    )

    result = service.discover()

    assert result.saved_count == 0
    assert result.source_unavailable is True
    assert result.errors == ["KAP source 404"]


def test_review_service_applies_ready_candidate_through_existing_service():
    repo = FakeCandidateRepo()
    saved = repo.upsert_discovered([_candidate(id=None, stock_id=47, status=CorporateActionCandidateStatus.READY)])[0]
    action = CorporateAction(
        id=5,
        stock_id=47,
        action_type=ActionType.BEDELSIZ,
        ex_date=date(2026, 5, 5),
        ratio=Decimal("6.3833834"),
        subscription_price=None,
        announcement_date=None,
        notes=None,
        applied=False,
    )
    corporate_action_service = MagicMock()
    corporate_action_service.get_by_stock.return_value = []
    corporate_action_service.register_bedelsiz.return_value = action
    corporate_action_service.apply_action.return_value = SimpleNamespace(description="ok")
    service = CorporateActionCandidateReviewService(
        candidate_repo=repo,
        corporate_action_service=corporate_action_service,
    )

    result = service.approve_and_apply(saved.id)

    corporate_action_service.register_bedelsiz.assert_called_once()
    corporate_action_service.apply_action.assert_called_once_with(5)
    assert result.candidate.status == CorporateActionCandidateStatus.APPLIED


def test_review_service_rejects_candidate_when_action_already_exists():
    repo = FakeCandidateRepo()
    saved = repo.upsert_discovered([_candidate(id=None, stock_id=47, status=CorporateActionCandidateStatus.READY)])[0]
    existing = CorporateAction(
        id=9,
        stock_id=47,
        action_type=ActionType.BEDELSIZ,
        ex_date=date(2026, 5, 5),
        ratio=Decimal("6.38340000"),
        subscription_price=None,
        announcement_date=None,
        notes=None,
        applied=True,
    )
    corporate_action_service = MagicMock()
    corporate_action_service.get_by_stock.return_value = [existing]
    service = CorporateActionCandidateReviewService(
        candidate_repo=repo,
        corporate_action_service=corporate_action_service,
    )

    with pytest.raises(ValueError, match="cakisir"):
        service.approve_and_apply(saved.id)

    corporate_action_service.register_bedelsiz.assert_not_called()
    corporate_action_service.apply_action.assert_not_called()
    assert repo.items[saved.id].status == CorporateActionCandidateStatus.NEEDS_REVIEW


def test_review_service_rejects_incomplete_candidate():
    repo = FakeCandidateRepo()
    saved = repo.upsert_discovered(
        [_candidate(stock_id=47, status=CorporateActionCandidateStatus.NEEDS_REVIEW, action_type=ActionType.BEDELLI)]
    )[0]
    service = CorporateActionCandidateReviewService(
        candidate_repo=repo,
        corporate_action_service=MagicMock(),
    )

    with pytest.raises(ValueError, match="eksik"):
        service.approve_and_apply(saved.id)

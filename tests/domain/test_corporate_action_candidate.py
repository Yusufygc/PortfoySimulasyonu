from datetime import date
from decimal import Decimal

import pytest

from src.domain.models.corporate_action import ActionType
from src.domain.models.corporate_action_candidate import (
    CorporateActionCandidate,
    CorporateActionCandidateStatus,
)


def test_bedelsiz_candidate_with_required_fields_is_ready():
    candidate = CorporateActionCandidate.discovered(
        ticker="MERKO",
        stock_id=47,
        source="kap_mkk",
        source_disclosure_id="1603760",
        action_type=ActionType.BEDELSIZ,
        ratio=Decimal("6.3833834"),
        ex_date=date(2026, 5, 5),
    )

    assert candidate.ticker == "MERKO"
    assert candidate.source == "KAP_MKK"
    assert candidate.status == CorporateActionCandidateStatus.READY


def test_bedelli_candidate_without_subscription_price_needs_review():
    candidate = CorporateActionCandidate.discovered(
        ticker="ABC.IS",
        stock_id=1,
        source="KAP_MKK",
        source_disclosure_id="1",
        action_type=ActionType.BEDELLI,
        ratio=Decimal("0.50"),
        ex_date=date(2026, 6, 1),
    )

    assert candidate.status == CorporateActionCandidateStatus.NEEDS_REVIEW


def test_candidate_rejects_invalid_confidence():
    with pytest.raises(ValueError, match="confidence"):
        CorporateActionCandidate.discovered(
            ticker="ABC.IS",
            stock_id=1,
            source="KAP_MKK",
            source_disclosure_id="1",
            action_type=ActionType.BEDELSIZ,
            ratio=Decimal("0.50"),
            ex_date=date(2026, 6, 1),
            confidence=Decimal("1.5"),
        )

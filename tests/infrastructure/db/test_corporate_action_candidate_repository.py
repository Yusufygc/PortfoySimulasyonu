from datetime import date
from decimal import Decimal

from src.domain.models.corporate_action import ActionType
from src.domain.models.corporate_action_candidate import (
    CorporateActionCandidate,
    CorporateActionCandidateStatus,
)
from src.infrastructure.db.sqlalchemy.repositories.sa_corporate_action_candidate_repository import (
    SQLAlchemyCorporateActionCandidateRepository,
)


def test_candidate_repository_maps_domain_to_orm():
    repo = SQLAlchemyCorporateActionCandidateRepository.__new__(SQLAlchemyCorporateActionCandidateRepository)
    candidate = CorporateActionCandidate(
        id=7,
        ticker="MERKO.IS",
        stock_id=47,
        source="KAP_MKK",
        source_disclosure_id="1603760",
        source_url="https://kap.org.tr/tr/Bildirim/1603760",
        action_type=ActionType.BEDELSIZ,
        status=CorporateActionCandidateStatus.READY,
        ratio=Decimal("6.3833834"),
        subscription_price=None,
        announcement_date=date(2026, 4, 30),
        ex_date=date(2026, 5, 5),
        confidence=Decimal("0.9"),
        raw_payload_json={"id": "1603760"},
        parse_notes=None,
    )

    orm = repo._to_orm(candidate)

    assert orm.id == 7
    assert orm.ticker == "MERKO.IS"
    assert orm.action_type == "BEDELSIZ"
    assert orm.status == "READY"
    assert orm.ratio == Decimal("6.3833834")
    assert orm.raw_payload_json == {"id": "1603760"}

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, NamedTuple, Optional

from src.domain.models.corporate_action import ActionType


def _validate_required_str(value: "str | None", field_name: str, *, uppercase: bool = True) -> str:
    normalized = (value or "").strip()
    if uppercase:
        normalized = normalized.upper()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _validate_candidate_numerics(ratio, subscription_price, confidence) -> None:
    if ratio is not None and ratio <= 0:
        raise ValueError("Candidate ratio must be positive when provided")
    if subscription_price is not None and subscription_price <= 0:
        raise ValueError("Subscription price must be positive when provided")
    if confidence < 0 or confidence > 1:
        raise ValueError("Candidate confidence must be between 0 and 1")


class CandidateDiscoveryData(NamedTuple):
    ticker: str
    source: str
    source_disclosure_id: str
    action_type: ActionType
    ratio: "Optional[Decimal]"
    ex_date: "Optional[date]"
    subscription_price: "Optional[Decimal]" = None
    stock_id: "Optional[int]" = None
    source_url: "Optional[str]" = None
    announcement_date: "Optional[date]" = None
    confidence: Decimal = Decimal("0.80")
    raw_payload_json: "Optional[dict[str, Any]]" = None
    parse_notes: "Optional[str]" = None


class CorporateActionCandidateStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    READY = "READY"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED = "APPROVED"
    APPLIED = "APPLIED"
    IGNORED = "IGNORED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class CorporateActionCandidate:
    """External disclosure normalized before a user approves portfolio impact."""

    id: Optional[int]
    ticker: str
    stock_id: Optional[int]
    source: str
    source_disclosure_id: str
    source_url: Optional[str]
    action_type: ActionType
    status: CorporateActionCandidateStatus
    ratio: Optional[Decimal]
    subscription_price: Optional[Decimal]
    announcement_date: Optional[date]
    ex_date: Optional[date]
    confidence: Decimal = Decimal("0")
    raw_payload_json: Optional[dict[str, Any]] = None
    parse_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", _validate_required_str(self.ticker, "Candidate ticker"))
        if not isinstance(self.action_type, ActionType):
            object.__setattr__(self, "action_type", ActionType(self.action_type))
        if not isinstance(self.status, CorporateActionCandidateStatus):
            object.__setattr__(self, "status", CorporateActionCandidateStatus(self.status))
        object.__setattr__(self, "source", _validate_required_str(self.source, "Candidate source"))
        object.__setattr__(
            self,
            "source_disclosure_id",
            _validate_required_str(self.source_disclosure_id, "Source disclosure id", uppercase=False),
        )
        _validate_candidate_numerics(self.ratio, self.subscription_price, self.confidence)

    @classmethod
    def discovered(cls, data: "CandidateDiscoveryData") -> "CorporateActionCandidate":
        return cls(
            id=None,
            ticker=data.ticker,
            stock_id=data.stock_id,
            source=data.source,
            source_disclosure_id=data.source_disclosure_id,
            source_url=data.source_url,
            action_type=data.action_type,
            status=cls.resolve_status(
                action_type=data.action_type,
                stock_id=data.stock_id,
                ratio=data.ratio,
                ex_date=data.ex_date,
                subscription_price=data.subscription_price,
            ),
            ratio=data.ratio,
            subscription_price=data.subscription_price,
            announcement_date=data.announcement_date,
            ex_date=data.ex_date,
            confidence=data.confidence,
            raw_payload_json=data.raw_payload_json,
            parse_notes=data.parse_notes,
        )

    @staticmethod
    def resolve_status(
        *,
        action_type: ActionType,
        stock_id: Optional[int],
        ratio: Optional[Decimal],
        ex_date: Optional[date],
        subscription_price: Optional[Decimal],
    ) -> CorporateActionCandidateStatus:
        if stock_id is None or ratio is None or ex_date is None:
            return CorporateActionCandidateStatus.NEEDS_REVIEW
        if action_type == ActionType.BEDELLI and subscription_price is None:
            return CorporateActionCandidateStatus.NEEDS_REVIEW
        return CorporateActionCandidateStatus.READY

    def with_status(self, status: CorporateActionCandidateStatus) -> "CorporateActionCandidate":
        return replace(self, status=status)

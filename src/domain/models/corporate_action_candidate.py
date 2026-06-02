from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from src.domain.models.corporate_action import ActionType


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
        ticker = (self.ticker or "").strip().upper()
        if not ticker:
            raise ValueError("Candidate ticker is required")
        object.__setattr__(self, "ticker", ticker)

        if not isinstance(self.action_type, ActionType):
            object.__setattr__(self, "action_type", ActionType(self.action_type))

        if not isinstance(self.status, CorporateActionCandidateStatus):
            object.__setattr__(
                self,
                "status",
                CorporateActionCandidateStatus(self.status),
            )

        source = (self.source or "").strip().upper()
        if not source:
            raise ValueError("Candidate source is required")
        object.__setattr__(self, "source", source)

        disclosure_id = (self.source_disclosure_id or "").strip()
        if not disclosure_id:
            raise ValueError("Source disclosure id is required")
        object.__setattr__(self, "source_disclosure_id", disclosure_id)

        if self.ratio is not None and self.ratio <= 0:
            raise ValueError("Candidate ratio must be positive when provided")
        if self.subscription_price is not None and self.subscription_price <= 0:
            raise ValueError("Subscription price must be positive when provided")
        if self.confidence < 0 or self.confidence > 1:
            raise ValueError("Candidate confidence must be between 0 and 1")

    @classmethod
    def discovered(
        cls,
        *,
        ticker: str,
        source: str,
        source_disclosure_id: str,
        action_type: ActionType,
        ratio: Optional[Decimal],
        ex_date: Optional[date],
        subscription_price: Optional[Decimal] = None,
        stock_id: Optional[int] = None,
        source_url: Optional[str] = None,
        announcement_date: Optional[date] = None,
        confidence: Decimal = Decimal("0.80"),
        raw_payload_json: Optional[dict[str, Any]] = None,
        parse_notes: Optional[str] = None,
    ) -> "CorporateActionCandidate":
        return cls(
            id=None,
            ticker=ticker,
            stock_id=stock_id,
            source=source,
            source_disclosure_id=source_disclosure_id,
            source_url=source_url,
            action_type=action_type,
            status=cls.resolve_status(
                action_type=action_type,
                stock_id=stock_id,
                ratio=ratio,
                ex_date=ex_date,
                subscription_price=subscription_price,
            ),
            ratio=ratio,
            subscription_price=subscription_price,
            announcement_date=announcement_date,
            ex_date=ex_date,
            confidence=confidence,
            raw_payload_json=raw_payload_json,
            parse_notes=parse_notes,
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

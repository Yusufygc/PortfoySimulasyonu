from __future__ import annotations

from dataclasses import dataclass

from src.application.services.corporate_actions.corporate_action_service import (
    CorporateActionResult,
    CorporateActionService,
)
from src.domain.models.corporate_action import ActionType, CorporateAction
from src.domain.models.corporate_action_candidate import (
    CorporateActionCandidate,
    CorporateActionCandidateStatus,
)
from src.domain.ports.repositories.i_corporate_action_candidate_repo import (
    ICorporateActionCandidateRepository,
)


@dataclass(frozen=True)
class CandidateApplyResult:
    candidate: CorporateActionCandidate
    action: CorporateAction
    result: CorporateActionResult


class CorporateActionCandidateReviewService:
    def __init__(
        self,
        *,
        candidate_repo: ICorporateActionCandidateRepository,
        corporate_action_service: CorporateActionService,
    ) -> None:
        self._candidate_repo = candidate_repo
        self._corporate_action_service = corporate_action_service

    def list_reviewable(self) -> list[CorporateActionCandidate]:
        return self._candidate_repo.get_by_statuses(
            [
                CorporateActionCandidateStatus.READY,
                CorporateActionCandidateStatus.NEEDS_REVIEW,
                CorporateActionCandidateStatus.APPROVED,
            ]
        )

    def approve_and_apply(self, candidate_id: int) -> CandidateApplyResult:
        candidate = self._require_candidate(candidate_id)
        self._validate_ready(candidate)
        existing_action = self._find_existing_action(candidate)
        if existing_action is not None:
            self._candidate_repo.update_status(candidate_id, CorporateActionCandidateStatus.NEEDS_REVIEW)
            raise ValueError(
                "Bu aday mevcut kurumsal islem kaydi ile cakisir: "
                f"action_id={existing_action.id}, stock_id={existing_action.stock_id}, "
                f"type={existing_action.action_type.value}, ex_date={existing_action.ex_date}"
            )
        self._candidate_repo.update_status(candidate_id, CorporateActionCandidateStatus.APPROVED)

        try:
            action = self._register_action(candidate)
            result = self._corporate_action_service.apply_action(action.id)
        except Exception:
            self._candidate_repo.update_status(candidate_id, CorporateActionCandidateStatus.NEEDS_REVIEW)
            raise

        applied_candidate = self._candidate_repo.update(candidate.with_status(CorporateActionCandidateStatus.APPLIED))
        return CandidateApplyResult(applied_candidate, action, result)

    def ignore(self, candidate_id: int) -> None:
        self._candidate_repo.update_status(candidate_id, CorporateActionCandidateStatus.IGNORED)

    def update_candidate(self, candidate: CorporateActionCandidate) -> CorporateActionCandidate:
        status = CorporateActionCandidate.resolve_status(
            action_type=candidate.action_type,
            stock_id=candidate.stock_id,
            ratio=candidate.ratio,
            ex_date=candidate.ex_date,
            subscription_price=candidate.subscription_price,
        )
        return self._candidate_repo.update(candidate.with_status(status))

    def _require_candidate(self, candidate_id: int) -> CorporateActionCandidate:
        candidate = self._candidate_repo.get_by_id(candidate_id)
        if candidate is None:
            raise ValueError(f"Kurumsal aksiyon adayi bulunamadi: id={candidate_id}")
        return candidate

    def _validate_ready(self, candidate: CorporateActionCandidate) -> None:
        if candidate.status not in (
            CorporateActionCandidateStatus.READY,
            CorporateActionCandidateStatus.APPROVED,
        ):
            raise ValueError("Aday uygulanmadan once eksik alanlar tamamlanmalidir.")
        if candidate.stock_id is None or candidate.ratio is None or candidate.ex_date is None:
            raise ValueError("Aday stock_id, ratio ve ex_date alanlari olmadan uygulanamaz.")
        if candidate.action_type == ActionType.BEDELLI and candidate.subscription_price is None:
            raise ValueError("Bedelli aday icin kullanim fiyati zorunludur.")

    def _find_existing_action(self, candidate: CorporateActionCandidate) -> CorporateAction | None:
        if candidate.stock_id is None or candidate.ex_date is None:
            return None
        for action in self._corporate_action_service.get_by_stock(candidate.stock_id):
            if action.action_type == candidate.action_type and action.ex_date == candidate.ex_date:
                return action
        return None

    def _register_action(self, candidate: CorporateActionCandidate) -> CorporateAction:
        notes = _candidate_notes(candidate)
        if candidate.action_type == ActionType.BEDELSIZ:
            return self._corporate_action_service.register_bedelsiz(
                stock_id=candidate.stock_id,
                ex_date=candidate.ex_date,
                ratio=candidate.ratio,
                announcement_date=candidate.announcement_date,
                notes=notes,
            )
        return self._corporate_action_service.register_bedelli(
            stock_id=candidate.stock_id,
            ex_date=candidate.ex_date,
            ratio=candidate.ratio,
            subscription_price=candidate.subscription_price,
            announcement_date=candidate.announcement_date,
            notes=notes,
        )


def _candidate_notes(candidate: CorporateActionCandidate) -> str:
    source_ref = f"{candidate.source}:{candidate.source_disclosure_id}"
    parts = [f"Otomatik aday kaynagi {source_ref}"]
    if candidate.source_url:
        parts.append(candidate.source_url)
    if candidate.parse_notes:
        parts.append(candidate.parse_notes)
    return " | ".join(parts)

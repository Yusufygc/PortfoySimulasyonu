from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List, Optional, Sequence

from src.domain.models.corporate_action_candidate import (
    CorporateActionCandidate,
    CorporateActionCandidateStatus,
)


class ICorporateActionCandidateRepository(ABC):
    @abstractmethod
    def get_by_id(self, candidate_id: int) -> Optional[CorporateActionCandidate]:
        raise NotImplementedError

    @abstractmethod
    def get_by_statuses(
        self,
        statuses: Sequence[CorporateActionCandidateStatus],
    ) -> List[CorporateActionCandidate]:
        raise NotImplementedError

    @abstractmethod
    def find_duplicate(self, candidate: CorporateActionCandidate) -> Optional[CorporateActionCandidate]:
        raise NotImplementedError

    @abstractmethod
    def upsert_discovered(
        self,
        candidates: Iterable[CorporateActionCandidate],
    ) -> List[CorporateActionCandidate]:
        raise NotImplementedError

    @abstractmethod
    def update(self, candidate: CorporateActionCandidate) -> CorporateActionCandidate:
        raise NotImplementedError

    @abstractmethod
    def update_status(
        self,
        candidate_id: int,
        status: CorporateActionCandidateStatus,
    ) -> None:
        raise NotImplementedError

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Sequence

from src.domain.models.corporate_action_candidate import CorporateActionCandidate


class CorporateActionProviderUnavailable(RuntimeError):
    """Raised when an external corporate action source is unavailable."""


class ICorporateActionProvider(ABC):
    @abstractmethod
    def fetch_candidates(
        self,
        tickers: Sequence[str],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[CorporateActionCandidate]:
        raise NotImplementedError

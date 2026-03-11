# src/domain/services_interfaces/i_risk_profile_repo.py

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.risk_profile import RiskProfile


class IRiskProfileRepository(ABC):
    """
    Risk Profili verilerine erişim arayüzü.
    """

    @abstractmethod
    def get_latest_profile(self) -> Optional[RiskProfile]:
        """En son kaydedilen risk profilini döner."""
        raise NotImplementedError

    @abstractmethod
    def save_profile(self, profile: RiskProfile) -> RiskProfile:
        """Yeni risk profili kaydeder."""
        raise NotImplementedError

    @abstractmethod
    def get_all_profiles(self) -> List[RiskProfile]:
        """Tüm profil geçmişini döner."""
        raise NotImplementedError

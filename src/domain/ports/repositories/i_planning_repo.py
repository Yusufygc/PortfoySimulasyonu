# src/domain/ports/repositories/i_planning_repo.py

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.budget import Budget
from src.domain.models.financial_goal import FinancialGoal


class IPlanningRepository(ABC):
    """
    Finansal Planlama (Bütçe & Hedefler) verilerine erişim arayüzü.

    Bu interface sayesinde:
        - MySQLPlanningRepository → Gerçek veritabanı
        - InMemoryPlanningRepository → Unit test
    şeklinde farklı implementasyonlar kullanılabilir.
    """

    # ==================== Budget İşlemleri ==================== #

    @abstractmethod
    def get_budget_by_month(self, month: str) -> Optional[Budget]:
        """
        Belirtilen ay için bütçe kaydını döner.

        Args:
            month: 'YYYY-MM' formatında ay string'i

        Returns:
            Budget veya None (kayıt yoksa)
        """
        raise NotImplementedError

    @abstractmethod
    def get_all_budgets(self) -> List[Budget]:
        """Tüm bütçe kayıtlarını tarih sırasına göre döner."""
        raise NotImplementedError

    @abstractmethod
    def upsert_budget(self, budget: Budget) -> Budget:
        """
        Bütçe kaydını oluşturur veya günceller.
        Aynı ay için zaten kayıt varsa günceller, yoksa yeni oluşturur.

        Args:
            budget: Kaydedilecek Budget nesnesi

        Returns:
            Kaydedilen Budget (id atanmış)
        """
        raise NotImplementedError

    @abstractmethod
    def delete_budget(self, budget_id: int) -> None:
        """Bütçe kaydını siler."""
        raise NotImplementedError

    # ==================== FinancialGoal İşlemleri ==================== #

    @abstractmethod
    def get_all_goals(self) -> List[FinancialGoal]:
        """Tüm finansal hedefleri döner."""
        raise NotImplementedError

    @abstractmethod
    def get_active_goals(self) -> List[FinancialGoal]:
        """Sadece aktif (ACTIVE) hedefleri döner."""
        raise NotImplementedError

    @abstractmethod
    def get_goal_by_id(self, goal_id: int) -> Optional[FinancialGoal]:
        """ID ile hedef getirir."""
        raise NotImplementedError

    @abstractmethod
    def insert_goal(self, goal: FinancialGoal) -> FinancialGoal:
        """
        Yeni bir hedef ekler.

        Returns:
            Kaydedilen FinancialGoal (id atanmış)
        """
        raise NotImplementedError

    @abstractmethod
    def update_goal(self, goal: FinancialGoal) -> None:
        """Mevcut hedefi günceller."""
        raise NotImplementedError

    @abstractmethod
    def delete_goal(self, goal_id: int) -> None:
        """Hedefi siler."""
        raise NotImplementedError

# src/domain/models/financial_goal.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


class GoalPriority:
    """Hedef öncelik sabitleri."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class GoalStatus:
    """Hedef durum sabitleri."""
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


@dataclass
class FinancialGoal:
    """
    Finansal hedefi temsil eder.
    Belirli bir birikime ulaşmak için tutar, vade ve ilerleme bilgisi tutar.
    'financial_goals' tablosunun domain karşılığı.
    """
    id: Optional[int]
    name: str                                   # Hedef adı (Araba, Ev, Tatil ...)
    target_amount: float                        # Hedef tutar (TL)
    current_amount: float = 0.0                 # Biriken tutar (TL)
    deadline: date = None                       # Hedef bitiş tarihi
    priority: str = GoalPriority.MEDIUM         # LOW / MEDIUM / HIGH
    status: str = GoalStatus.ACTIVE             # ACTIVE / COMPLETED

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # ---------- Hesaplanan Özellikler ---------- #

    @property
    def remaining_amount(self) -> float:
        """Hedefe ulaşmak için kalan tutar."""
        return max(self.target_amount - self.current_amount, 0.0)

    @property
    def progress_ratio(self) -> float:
        """İlerleme oranı (0.0 - 1.0)."""
        if self.target_amount <= 0:
            return 0.0
        return min(self.current_amount / self.target_amount, 1.0)

    @property
    def is_completed(self) -> bool:
        """Hedef tamamlandı mı?"""
        return self.current_amount >= self.target_amount

    def months_remaining(self) -> int:
        """Vadeye kalan ay sayısı. Geçmişte ise 0."""
        if self.deadline is None:
            return 0
        today = date.today()
        if self.deadline <= today:
            return 0
        delta_years = self.deadline.year - today.year
        delta_months = self.deadline.month - today.month
        return max(delta_years * 12 + delta_months, 0)

    def required_monthly_contribution(self) -> float:
        """Hedefe ulaşmak için gereken aylık katkı."""
        months = self.months_remaining()
        if months <= 0:
            return self.remaining_amount  # Vade geçmiş, tamamını hemen öde
        return self.remaining_amount / months

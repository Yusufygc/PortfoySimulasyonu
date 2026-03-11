# src/domain/models/budget.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Budget:
    """
    Aylık bütçe kaydını temsil eder.
    Gelir, gider kalemleri ve tasarruf hedefini tutar.
    'budgets' tablosunun domain karşılığı.
    """
    id: Optional[int]
    month: str                          # Format: 'YYYY-MM'

    # Gelirler
    income_salary: float = 0.0          # Maaş geliri
    income_additional: float = 0.0      # Ek gelirler

    # Giderler
    expense_rent: float = 0.0           # Kira / Konut
    expense_bills: float = 0.0          # Faturalar
    expense_food: float = 0.0           # Market / Mutfak
    expense_transport: float = 0.0      # Ulaşım
    expense_luxury: float = 0.0         # Eğlence / Lüks

    # Hedef
    savings_target: float = 0.0         # Hedeflenen aylık tasarruf

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # ---------- Hesaplanan Özellikler ---------- #

    @property
    def total_income(self) -> float:
        """Toplam gelir."""
        return self.income_salary + self.income_additional

    @property
    def total_expense(self) -> float:
        """Toplam gider."""
        return (
            self.expense_rent
            + self.expense_bills
            + self.expense_food
            + self.expense_transport
            + self.expense_luxury
        )

    @property
    def net_savings_potential(self) -> float:
        """Net tasarruf potansiyeli = Gelir - Gider."""
        return self.total_income - self.total_expense

    @property
    def status_message(self) -> str:
        """Bütçe durumu hakkında otomatik mesaj."""
        net = self.net_savings_potential
        if net < 0:
            return "⚠️ DİKKAT: Geliriniz giderlerinizi karşılamıyor! (Açık Veriyorsunuz)"
        elif net < self.savings_target:
            return "📉 Hedeflenen tasarrufun altındasınız. Harcamaları kısmanız önerilir."
        else:
            return "✅ Harika! Hedeflenen tasarrufu gerçekleştirebilirsiniz."

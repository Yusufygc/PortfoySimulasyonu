# src/domain/models/budget.py

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class BudgetItem:
    """Tek bir gelir veya gider kalemi."""
    id: Optional[int]
    budget_id: Optional[int]
    item_type: str    # 'income' | 'expense'
    name: str
    amount: float = 0.0


@dataclass
class Budget:
    """
    Aylık bütçe kaydını temsil eder.
    Gelir/gider kalemleri BudgetItem listesi ile dinamik olarak tutulur.
    'budgets' + 'budget_items' tablolarının domain karşılığı.
    """
    id: Optional[int]
    month: str                          # Format: 'YYYY-MM'
    savings_target: float = 0.0
    items: List[BudgetItem] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # ---------- Hesaplanan Özellikler ---------- #

    @property
    def total_income(self) -> float:
        """Toplam gelir."""
        return sum(i.amount for i in self.items if i.item_type == 'income')

    @property
    def total_expense(self) -> float:
        """Toplam gider."""
        return sum(i.amount for i in self.items if i.item_type == 'expense')

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

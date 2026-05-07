# src/domain/models/corporate_action.py

from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional


class ActionType(str, Enum):
    BEDELLI = "BEDELLI"
    BEDELSIZ = "BEDELSIZ"


@dataclass(frozen=True)
class CorporateAction:
    """
    Bedelli veya bedelsiz sermaye artırımı olayını temsil eder.

    Borsa İstanbul kuralları:
      - Bedelsiz: İç kaynaklardan (yedek akçe, kâr) hissedara bedavaya yeni pay.
        Oran (ratio) → yeni_pay = mevcut_adet * ratio  (kesir kabul edilmez, küçüğe yuvarlanır)
        Teorik baz fiyat = eski_fiyat / (1 + ratio)

      - Bedelli (Rüçhan Hakkı Kullanımı): Hissedar kullanım fiyatından yeni pay satın alır.
        Teorik baz fiyat = (N × P + M × K) / (N + M)
        N=1, M=ratio, P=piyasa fiyatı, K=subscription_price

    applied=True: Bu aksiyon portföye zaten uygulandı, tekrar uygulanamaz.
    """
    id: Optional[int]
    stock_id: int
    action_type: ActionType
    ex_date: date
    ratio: Decimal                          # Artırım oranı  (örn. 0.50 → %50)
    subscription_price: Optional[Decimal]   # Sadece BEDELLI için (kullanım fiyatı)
    announcement_date: Optional[date]
    notes: Optional[str]
    applied: bool

    # ──────────────── Factory Methods ────────────────

    @classmethod
    def create_bedelsiz(
        cls,
        stock_id: int,
        ex_date: date,
        ratio: Decimal,
        announcement_date: Optional[date] = None,
        notes: Optional[str] = None,
    ) -> "CorporateAction":
        if ratio <= 0:
            raise ValueError("Artırım oranı sıfırdan büyük olmalıdır")
        return cls(
            id=None,
            stock_id=stock_id,
            action_type=ActionType.BEDELSIZ,
            ex_date=ex_date,
            ratio=ratio,
            subscription_price=None,
            announcement_date=announcement_date,
            notes=notes,
            applied=False,
        )

    @classmethod
    def create_bedelli(
        cls,
        stock_id: int,
        ex_date: date,
        ratio: Decimal,
        subscription_price: Decimal,
        announcement_date: Optional[date] = None,
        notes: Optional[str] = None,
    ) -> "CorporateAction":
        if ratio <= 0:
            raise ValueError("Artırım oranı sıfırdan büyük olmalıdır")
        if subscription_price is None or subscription_price <= 0:
            raise ValueError("Bedelli artırım için kullanım fiyatı (rüçhan fiyatı) sıfırdan büyük olmalıdır")
        return cls(
            id=None,
            stock_id=stock_id,
            action_type=ActionType.BEDELLI,
            ex_date=ex_date,
            ratio=ratio,
            subscription_price=subscription_price,
            announcement_date=announcement_date,
            notes=notes,
            applied=False,
        )

    # ──────────────── Hesaplama Yardımcıları ────────────────

    @property
    def ratio_percent(self) -> Decimal:
        """Oranı yüzde olarak döner (örn. 0.50 → 50.00)."""
        return self.ratio * Decimal("100")

    def calculate_new_shares(self, current_quantity: int) -> int:
        """
        Mevcut pozisyon üzerinden BİST kuralına uygun yeni pay hesabı.
        Küsurat oluşmaz → Python int() → küçüğe yuvarlar (floor).
        """
        return int(Decimal(str(current_quantity)) * self.ratio)

    def theoretical_price(self, current_price: Decimal) -> Decimal:
        """
        Teorik baz fiyat hesabı (BİST yöntemi).

        Bedelsiz : P_teorik = P / (1 + oran)
        Bedelli  : P_teorik = (1 × P + oran × K) / (1 + oran)
        """
        if self.action_type == ActionType.BEDELSIZ:
            return current_price / (Decimal("1") + self.ratio)
        else:
            k = self.subscription_price
            return (current_price + self.ratio * k) / (Decimal("1") + self.ratio)

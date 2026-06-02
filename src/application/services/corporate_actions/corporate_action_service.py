# src/application/services/corporate_actions/corporate_action_service.py
"""
Borsa İstanbul kurallarına uygun bedelli / bedelsiz sermaye artırımı servisi.

Akış:
  1. Kullanıcı register_bedelli / register_bedelsiz ile aksiyonu sisteme kaydeder.
  2. Uygun zamanda apply_action çağrılır.
  3. Servis, mevcut pozisyonu hesaplar ve BİST kuralına göre yeni hisse adetini belirler.
  4. Bedelsiz → sıfır maliyetli sentetik BUY eklenir (toplam maliyet sabit kalır, ortalama düşer).
     Bedelli → kullanım fiyatından sentetik BUY eklenir (sermayeden düşer, ortalama değişir).
  5. Aksiyon "applied" olarak işaretlenir.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional

from src.domain.models.corporate_action import ActionType, CorporateAction
from src.domain.models.position import Position
from src.domain.models.trade import Trade, TradeSide
from src.domain.ports.repositories.i_corporate_action_repo import ICorporateActionRepository
from src.domain.ports.repositories.i_portfolio_repo import IPortfolioRepository
from src.application.services.corporate_actions.price_adjustment_service import (
    CorporateActionPriceAdjustmentService,
)


@dataclass
class CorporateActionResult:
    """apply_action işleminin sonuç raporu."""
    action_id: int
    action_type: ActionType
    stock_id: int

    shares_before: int
    new_shares: int
    shares_after: int

    avg_cost_before: Optional[Decimal]
    avg_cost_after: Optional[Decimal]

    theoretical_ex_price: Optional[Decimal]  # Teorik baz fiyat (BİST)
    capital_spent: Decimal                    # Bedelli için ödenen tutar

    description: str
    price_adjustment_factor: Optional[Decimal] = None
    price_adjustment_count: int = 0


def _bedelsiz_description(
    action: CorporateAction,
    shares_before: int,
    new_shares: int,
    new_qty: int,
    avg_cost_before: Decimal,
    avg_cost_after: Decimal,
    theoretical_price: Optional[Decimal],
) -> str:
    pct = float(action.ratio_percent)
    desc = (
        f"Bedelsiz Sermaye Artırımı %{pct:.0f} — "
        f"ex-date: {action.ex_date} | "
        f"{shares_before} lot + {new_shares} bedelsiz lot = {new_qty} lot | "
        f"Ort. maliyet: {avg_cost_before:.4f} → {avg_cost_after:.4f} TL"
    )
    if theoretical_price is not None:
        desc += f" | Teorik baz fiyat: {theoretical_price:.4f} TL"
    return desc


def _bedelli_description(
    action: CorporateAction,
    shares_before: int,
    new_shares: int,
    new_qty: int,
    avg_cost_before: Decimal,
    avg_cost_after: Decimal,
    capital_spent: Decimal,
    theoretical_price: Optional[Decimal],
) -> str:
    pct = float(action.ratio_percent)
    sub_price = action.subscription_price
    desc = (
        f"Bedelli Sermaye Artırımı %{pct:.0f} — "
        f"ex-date: {action.ex_date} | "
        f"Kullanım fiyatı: {sub_price:.4f} TL | "
        f"{shares_before} lot + {new_shares} yeni lot = {new_qty} lot | "
        f"Sermaye kullanımı: {capital_spent:.2f} TL | "
        f"Ort. maliyet: {avg_cost_before:.4f} → {avg_cost_after:.4f} TL"
    )
    if theoretical_price is not None:
        desc += f" | Teorik baz fiyat: {theoretical_price:.4f} TL"
    return desc


def _build_action_result(
    action: CorporateAction,
    shares_before: int,
    new_shares: int,
    shares_after: int,
    avg_cost_before: Optional[Decimal],
    avg_cost_after: Optional[Decimal],
    theoretical_price: Optional[Decimal],
    capital_spent: Decimal,
    description: str,
    price_adjustment_factor: Optional[Decimal] = None,
    price_adjustment_count: int = 0,
) -> CorporateActionResult:
    return CorporateActionResult(
        action_id=action.id,
        action_type=action.action_type,
        stock_id=action.stock_id,
        shares_before=shares_before,
        new_shares=new_shares,
        shares_after=shares_after,
        avg_cost_before=avg_cost_before,
        avg_cost_after=avg_cost_after,
        theoretical_ex_price=theoretical_price,
        capital_spent=capital_spent,
        description=description,
        price_adjustment_factor=price_adjustment_factor,
        price_adjustment_count=price_adjustment_count,
    )


class CorporateActionService:
    """
    Bedelli / Bedelsiz Sermaye Artırımı uygulama servisi.

    Bağımlılıklar:
      - action_repo  : Kurumsal aksiyon kayıtlarını okur / yazar.
      - portfolio_repo: Mevcut trade'leri okur ve sentetik BUY ekler.
    """

    def __init__(
        self,
        action_repo: ICorporateActionRepository,
        portfolio_repo: IPortfolioRepository,
        price_adjustment_service: CorporateActionPriceAdjustmentService | None = None,
    ) -> None:
        self._action_repo = action_repo
        self._portfolio_repo = portfolio_repo
        self._price_adjustment_service = price_adjustment_service

    # ══════════════════════════════════════════════════════════
    #  KAYIT (REGISTRATION)
    # ══════════════════════════════════════════════════════════

    def register_bedelsiz(
        self,
        stock_id: int,
        ex_date: date,
        ratio: Decimal,
        announcement_date: Optional[date] = None,
        notes: Optional[str] = None,
    ) -> CorporateAction:
        """
        Bedelsiz sermaye artırımı kaydeder (henüz portföye uygulamaz).

        ratio: Artırım oranı — 0.50 → %50 bedelsiz.
               BİST en yaygın oranları: %10, %20, %25, %50, %100
        """
        action = CorporateAction.create_bedelsiz(
            stock_id=stock_id,
            ex_date=ex_date,
            ratio=ratio,
            announcement_date=announcement_date,
            notes=notes,
        )
        self._ensure_not_registered(action)
        return self._action_repo.insert(action)

    def register_bedelli(
        self,
        stock_id: int,
        ex_date: date,
        ratio: Decimal,
        subscription_price: Decimal,
        announcement_date: Optional[date] = None,
        notes: Optional[str] = None,
    ) -> CorporateAction:
        """
        Bedelli sermaye artırımı (rüçhan hakkı kullanımı) kaydeder.

        ratio             : Artırım oranı (örn. 0.20 → %20)
        subscription_price: Rüçhan hakkı kullanım fiyatı (genellikle nominal değer = 1 TL)
        """
        action = CorporateAction.create_bedelli(
            stock_id=stock_id,
            ex_date=ex_date,
            ratio=ratio,
            subscription_price=subscription_price,
            announcement_date=announcement_date,
            notes=notes,
        )
        self._ensure_not_registered(action)
        return self._action_repo.insert(action)

    # ══════════════════════════════════════════════════════════
    #  SORGULAR (QUERIES)
    # ══════════════════════════════════════════════════════════

    def get_all(self) -> List[CorporateAction]:
        return self._action_repo.get_all()

    def get_by_stock(self, stock_id: int) -> List[CorporateAction]:
        return self._action_repo.get_by_stock(stock_id)

    def get_pending(self) -> List[CorporateAction]:
        return self._action_repo.get_all_pending()

    def get_pending_by_stock(self, stock_id: int) -> List[CorporateAction]:
        return self._action_repo.get_pending_by_stock(stock_id)

    def _ensure_not_registered(self, candidate: CorporateAction) -> None:
        for existing in self._action_repo.get_by_stock(candidate.stock_id):
            if _same_registration(existing, candidate):
                raise ValueError(
                    "Ayni hisse, islem tipi ve ex-date icin kurumsal islem zaten kayitli: "
                    f"id={existing.id}, stock_id={existing.stock_id}, "
                    f"type={existing.action_type.value}, ex_date={existing.ex_date}"
                )

    # ══════════════════════════════════════════════════════════
    #  UYGULAMA (APPLICATION)
    # ══════════════════════════════════════════════════════════

    def apply_action(
        self,
        action_id: int,
        current_price: Optional[Decimal] = None,
    ) -> CorporateActionResult:
        """
        Kaydedilmiş bir aksiyonu portföye uygular.

        current_price verilirse teorik baz fiyat da hesaplanır.
        Aksiyon daha önce uygulanmışsa ValueError fırlatır.
        """
        action = self._action_repo.get_by_id(action_id)
        if action is None:
            raise ValueError(f"Kurumsal işlem bulunamadı: id={action_id}")
        if action.applied:
            raise ValueError(
                f"Bu kurumsal işlem zaten uygulanmış: id={action_id} "
                f"({action.action_type.value} — ex_date={action.ex_date})"
            )

        trades = self._portfolio_repo.get_trades_by_stock(action.stock_id)
        position = Position.from_trades(action.stock_id, trades)

        if position.total_quantity == 0:
            raise ValueError(
                f"Portföyde bu hisse bulunmuyor (stock_id={action.stock_id}). "
                "Kurumsal işlem uygulamak için açık pozisyon gereklidir."
            )

        new_shares = action.calculate_new_shares(position.total_quantity)
        if new_shares <= 0:
            raise ValueError(
                f"Hesaplanan yeni hisse sayısı sıfır. "
                f"Mevcut pozisyon ({position.total_quantity} lot) ile "
                f"%{float(action.ratio_percent):.0f} oran yeterli değil."
            )

        theoretical = action.theoretical_price(current_price) if current_price else None

        if action.action_type == ActionType.BEDELSIZ:
            result = self._apply_bedelsiz(action, position, new_shares, theoretical)
        else:
            result = self._apply_bedelli(action, position, new_shares, theoretical)

        self._action_repo.mark_applied(action_id)
        return self._with_price_adjustment(result, action)

    def adjust_prices_for_action(self, action_id: int):
        if self._price_adjustment_service is None:
            raise ValueError("Fiyat gecmisi duzeltme servisi yapilandirilmamis.")
        return self._price_adjustment_service.adjust_prices_for_action(action_id)

    def _with_price_adjustment(
        self,
        result: CorporateActionResult,
        action: CorporateAction,
    ) -> CorporateActionResult:
        if self._price_adjustment_service is None:
            return result

        adjustment = self._price_adjustment_service.adjust_prices_for_applied_action(action)
        return _build_action_result(
            action=action,
            shares_before=result.shares_before,
            new_shares=result.new_shares,
            shares_after=result.shares_after,
            avg_cost_before=result.avg_cost_before,
            avg_cost_after=result.avg_cost_after,
            theoretical_price=result.theoretical_ex_price,
            capital_spent=result.capital_spent,
            description=result.description,
            price_adjustment_factor=adjustment.factor,
            price_adjustment_count=adjustment.adjusted_count,
        )

    # ──────────────── İç Uygulama Metotları ────────────────

    def _apply_bedelsiz(
        self,
        action: CorporateAction,
        position: Position,
        new_shares: int,
        theoretical_price: Optional[Decimal],
    ) -> CorporateActionResult:
        """
        Bedelsiz artırım uygulama:
        Portföydeki toplam maliyet sabit kalır; hisse adedi artar; ortalama maliyet düşer.

        Sentetik BUY işlemi fiyat=0 TL ile eklenir.
        Trade dataclass fabrika metodu price>0 zorlar, bu yüzden Trade'i
        doğrudan oluştururuz (iç domain nesnesi, validation bypass gerekli değil —
        bedelsiz sermaye artırımı gerçek bir para hareketi değildir).
        """
        avg_cost_before = position.average_cost
        shares_before = position.total_quantity

        # Fiyat=0 sentetik BUY: toplam_maliyet değişmez
        synthetic_trade = Trade(
            id=None,
            stock_id=action.stock_id,
            trade_date=action.ex_date,
            trade_time=None,
            side=TradeSide.BUY,
            quantity=new_shares,
            price=Decimal("0"),
        )
        self._portfolio_repo.insert_trade(synthetic_trade)

        # Yeni ortalama maliyet: aynı toplam maliyet / daha fazla hisse
        new_qty = shares_before + new_shares
        avg_cost_after = (position.total_cost / Decimal(str(new_qty))) if new_qty > 0 else Decimal("0")

        return _build_action_result(
            action=action,
            shares_before=shares_before,
            new_shares=new_shares,
            shares_after=new_qty,
            avg_cost_before=avg_cost_before,
            avg_cost_after=avg_cost_after,
            theoretical_price=theoretical_price,
            capital_spent=Decimal("0"),
            description=_bedelsiz_description(
                action, shares_before, new_shares, new_qty, avg_cost_before, avg_cost_after, theoretical_price
            ),
        )

    def _apply_bedelli(
        self,
        action: CorporateAction,
        position: Position,
        new_shares: int,
        theoretical_price: Optional[Decimal],
    ) -> CorporateActionResult:
        """
        Bedelli artırım (rüçhan hakkı kullanımı):
        Hissedar subscription_price fiyatından yeni pay satın alır.
        Bu, portföy sermayesinden düşülür (sentetik BUY ile otomatik yansır).
        """
        avg_cost_before = position.average_cost
        shares_before = position.total_quantity
        sub_price = action.subscription_price
        capital_spent = sub_price * Decimal(str(new_shares))

        # Rüçhan hakkı kullanım fiyatından BUY → sermayeden düşer
        synthetic_trade = Trade.create_buy(
            stock_id=action.stock_id,
            trade_date=action.ex_date,
            quantity=new_shares,
            price=sub_price,
        )
        self._portfolio_repo.insert_trade(synthetic_trade)

        new_qty = shares_before + new_shares
        new_total_cost = position.total_cost + capital_spent
        avg_cost_after = new_total_cost / Decimal(str(new_qty)) if new_qty > 0 else Decimal("0")

        return _build_action_result(
            action=action,
            shares_before=shares_before,
            new_shares=new_shares,
            shares_after=new_qty,
            avg_cost_before=avg_cost_before,
            avg_cost_after=avg_cost_after,
            theoretical_price=theoretical_price,
            capital_spent=capital_spent,
            description=_bedelli_description(
                action, shares_before, new_shares, new_qty, avg_cost_before, avg_cost_after, capital_spent, theoretical_price
            ),
        )

    # ══════════════════════════════════════════════════════════
    #  YÖNETİM
    # ══════════════════════════════════════════════════════════

    def delete_action(self, action_id: int) -> None:
        """Henüz uygulanmamış bir aksiyonu siler."""
        action = self._action_repo.get_by_id(action_id)
        if action is None:
            raise ValueError(f"Kurumsal işlem bulunamadı: id={action_id}")
        if action.applied:
            raise ValueError("Uygulanmış bir kurumsal işlem silinemez.")
        self._action_repo.delete(action_id)


def _same_registration(left: CorporateAction, right: CorporateAction) -> bool:
    return (
        left.stock_id == right.stock_id
        and left.action_type == right.action_type
        and left.ex_date == right.ex_date
    )

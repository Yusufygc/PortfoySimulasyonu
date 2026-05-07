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
    ) -> None:
        self._action_repo = action_repo
        self._portfolio_repo = portfolio_repo

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

        # mark_applied önce işaretlenir; insert_trade başarısız olursa
        # aksiyon "applied" kalır ama çift uygulama riski önlenir.
        self._action_repo.mark_applied(action_id)

        if action.action_type == ActionType.BEDELSIZ:
            result = self._apply_bedelsiz(action, position, new_shares, theoretical)
        else:
            result = self._apply_bedelli(action, position, new_shares, theoretical)

        return result

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

        pct = float(action.ratio_percent)
        desc = (
            f"Bedelsiz Sermaye Artırımı %{pct:.0f} — "
            f"ex-date: {action.ex_date} | "
            f"{shares_before} lot + {new_shares} bedelsiz lot = {new_qty} lot | "
            f"Ort. maliyet: {avg_cost_before:.4f} → {avg_cost_after:.4f} TL"
        )
        if theoretical_price is not None:
            desc += f" | Teorik baz fiyat: {theoretical_price:.4f} TL"

        return CorporateActionResult(
            action_id=action.id,
            action_type=action.action_type,
            stock_id=action.stock_id,
            shares_before=shares_before,
            new_shares=new_shares,
            shares_after=new_qty,
            avg_cost_before=avg_cost_before,
            avg_cost_after=avg_cost_after,
            theoretical_ex_price=theoretical_price,
            capital_spent=Decimal("0"),
            description=desc,
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

        pct = float(action.ratio_percent)
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

        return CorporateActionResult(
            action_id=action.id,
            action_type=action.action_type,
            stock_id=action.stock_id,
            shares_before=shares_before,
            new_shares=new_shares,
            shares_after=new_qty,
            avg_cost_before=avg_cost_before,
            avg_cost_after=avg_cost_after,
            theoretical_ex_price=theoretical_price,
            capital_spent=capital_spent,
            description=desc,
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

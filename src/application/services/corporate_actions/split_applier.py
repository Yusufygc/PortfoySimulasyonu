"""Bölünme kararının defterlere ve fiyat geçmişine uygulanması / geri alınması.

Sıra:
1. Ana portföy, model portföy ve varlık defteri işlemleri `allocate_split` ile yeniden hesaplanır; küsurat lotlar
   ex-date sonrası ilk kapanışla nakde çevrilir. Hepsi `ISplitLedgerRepository.apply` ile tek işlemde yazılır.
2. BIST hissesinde SQLite fiyat geçmişi yalnızca seri bölünme kırılmasını gerçekten gösteriyorsa düzeltilir;
   Yahoo geçmişi zaten düzelttiyse (kırılma yok) fiyatlara dokunulmaz, böylece çift düzeltme olmaz.
3. Olay `corporate_actions` tablosuna uygulanmış bedelsiz olarak, DuckDB'ye portföy olayı olarak kaydedilir
   (mevcut aday eleme ve piyasa geçmişi düzeltmesi aynı kaydı görür).
Fiyat adımı başarısız olsa bile işlem düzeltmesi geri alınmaz (işlemler doğrudur); hata loglanır.
"""
from __future__ import annotations

import logging
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from typing import List, NamedTuple, Optional, Tuple

from src.domain.models.corporate_action import CorporateAction
from src.domain.models.market_corporate_action import MarketActionStatus
from src.domain.models.split_event import (
    SplitCashEntry,
    SplitEvent,
    SplitLedger,
    SplitLedgerSnapshot,
    SplitTradeChange,
)
from src.domain.models.split_signal import SplitDecision
from src.domain.ports.repositories.i_corporate_action_repo import ICorporateActionRepository
from src.domain.ports.repositories.i_price_repo import IPriceRepository
from src.domain.ports.repositories.i_split_ledger_repo import ISplitLedgerRepository
from src.domain.ports.services.i_split_signal_provider import SplitTarget
from src.domain.split_detection import persistent_breaks
from src.domain.split_math import allocate_split

logger = logging.getLogger(__name__)

_PRICE_WINDOW_DAYS = 15
_BREAK_MATCH_TOLERANCE = Decimal("0.15")


class SplitApplierDeps(NamedTuple):
    ledger_repo: ISplitLedgerRepository
    price_repo: IPriceRepository
    corporate_action_repo: ICorporateActionRepository
    market_action_service: object = None  # MarketCorporateActionService; yoksa DuckDB kaydı atlanır


def plan_changes(
    snapshot: SplitLedgerSnapshot,
    decision: SplitDecision,
    post_ex_close: Optional[Decimal],
) -> Tuple[Tuple[SplitTradeChange, ...], Tuple[SplitCashEntry, ...]]:
    """Defterlerdeki işlem değişiklikleri ve küsurat nakdi (saf hesap)."""
    changes: List[SplitTradeChange] = []
    cash: List[SplitCashEntry] = []
    for (ledger, portfolio_id), lots in sorted(snapshot.lots.items(), key=lambda item: (item[0][0].value, item[0][1] or 0)):
        allocation = allocate_split(lots, decision.ex_date, decision.multiplier, whole_lots=ledger != SplitLedger.ASSET)
        changes.extend(
            SplitTradeChange(ledger, a.trade_id, a.pre_quantity, a.post_quantity, a.pre_price, a.post_price, portfolio_id)
            for a in allocation.adjustments
        )
        amount = allocation.fraction_cash(post_ex_close, Decimal("1"))
        if amount > 0 and ledger != SplitLedger.ASSET:
            cash.append(SplitCashEntry(ledger, amount, decision.ex_date, portfolio_id))
    return tuple(changes), tuple(cash)


def _matching_break(closes, expected: Decimal) -> Optional[date]:
    """SQLite serisinde bölünme çarpanına (±%15) uyan kalıcı kırılmanın günü."""
    for point_date, multiplier in persistent_breaks(closes):
        if abs(Decimal(str(multiplier)) / expected - 1) <= _BREAK_MATCH_TOLERANCE:
            return point_date
    return None


class SplitApplier:
    def __init__(self, deps: SplitApplierDeps) -> None:
        self._ledger = deps.ledger_repo
        self._prices = deps.price_repo
        self._actions = deps.corporate_action_repo
        self._market = deps.market_action_service

    # ---- uygula ------------------------------------------------------------------------
    def apply(self, decision: SplitDecision, target: SplitTarget, auto_applied: bool) -> SplitEvent:
        if decision.multiplier <= 1:
            raise ValueError("Ters bölünme otomatik uygulanmaz; kullanıcı kararı gerekir.")
        snapshot = self._ledger.load_snapshot(stock_id=target.stock_id, asset_id=target.asset_id)
        changes, cash = plan_changes(snapshot, decision, self._post_ex_close(target, decision.ex_date))
        event = self._ledger.apply(SplitEvent(
            id=None, ticker=decision.ticker, ex_date=decision.ex_date, multiplier=decision.multiplier,
            sources=",".join(s.value for s in decision.sources), auto_applied=auto_applied,
            stock_id=target.stock_id, asset_id=target.asset_id if target.stock_id is None else None,
            trade_changes=changes, cash_entries=cash,
        ))
        if target.stock_id is not None:
            self._sync_bist_history(event, target)
        return self._ledger.get_event(event.id) or event

    def _post_ex_close(self, target: SplitTarget, ex_date: date) -> Optional[Decimal]:
        if target.stock_id is None:
            return None
        series = self._prices.get_price_series(target.stock_id, ex_date, ex_date + timedelta(days=_PRICE_WINDOW_DAYS))
        first = min(series, key=lambda p: p.price_date, default=None)
        return first.close_price if first is not None else None

    def _sync_bist_history(self, event: SplitEvent, target: SplitTarget) -> None:
        # Her adım tamamlanır tamamlanmaz kayda geçer: sonraki adım düşse bile geri alma neyi geri çevireceğini bilir.
        try:
            before_date, count = self._adjust_sqlite_prices(event)
            self._ledger.record_price_adjustment(event.id, before_date, count, None)
            action = self._register_corporate_action(event, count)
            effective = self._register_market_action(target, action)
            if effective is not None:
                self._ledger.record_price_adjustment(event.id, before_date, count, effective)
        except Exception as exc:  # işlemler doğru; fiyat geçmişi sonra yeniden kurulabilir
            logger.warning("Bölünme fiyat geçmişi eşitlenemedi (%s %s): %s", event.ticker, event.ex_date, exc,
                           exc_info=True)

    def _adjust_sqlite_prices(self, event: SplitEvent) -> Tuple[Optional[date], int]:
        window = timedelta(days=_PRICE_WINDOW_DAYS)
        series = self._prices.get_price_series(event.stock_id, event.ex_date - window, event.ex_date + window)
        closes = [(p.price_date, float(p.close_price)) for p in series]
        before_date = _matching_break(closes, event.multiplier)
        if before_date is None:
            logger.info("%s fiyat geçmişi bölünmeye göre zaten tutarlı; fiyatlar değişmedi", event.ticker)
            return None, 0
        count = self._prices.adjust_prices_before_date(event.stock_id, before_date, Decimal("1") / event.multiplier)
        return before_date, count

    def _register_corporate_action(self, event: SplitEvent, adjusted_count: int) -> CorporateAction:
        note = f"Otomatik bölünme {event.multiplier.normalize()}:1 ({event.sources})"
        action = self._actions.insert(CorporateAction.create_bedelsiz(
            stock_id=event.stock_id, ex_date=event.ex_date, ratio=event.multiplier - Decimal("1"), notes=note,
        ))
        factor = Decimal("1") / event.multiplier
        self._actions.mark_applied(action.id)
        self._actions.mark_prices_adjusted(action.id, factor, adjusted_count)
        self._ledger.set_corporate_action(event.id, action.id)
        return replace(action, applied=True, price_adjustment_factor=factor)

    def _register_market_action(self, target: SplitTarget, action: CorporateAction) -> Optional[date]:
        if self._market is None:
            return None
        stored = self._market.register_portfolio_action(target.key, action)
        if stored is None or stored.status != MarketActionStatus.CONFIRMED:
            return None  # ham seride kırılma yok (Yahoo zaten düzeltmiş): DuckDB fiyatlarına etkisi yok
        return stored.effective_date

    # ---- geri al -----------------------------------------------------------------------
    def revert(self, event_id: int) -> SplitEvent:
        event = self._ledger.revert(event_id)  # çakışmada istisna: fiyatlara dokunulmaz
        if event.stock_id is not None and event.price_adjusted_before and event.price_adjustment_count:
            self._prices.adjust_prices_before_date(event.stock_id, event.price_adjusted_before, event.multiplier)
        if self._market is not None and event.market_effective_date:
            self._market.set_status(event.ticker, event.market_effective_date, MarketActionStatus.IGNORED)
        if event.corporate_action_id is not None:
            self._actions.delete(event.corporate_action_id)
        return event

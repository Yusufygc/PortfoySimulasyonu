"""Otomatik hisse bölünmesi: tara -> uzlaştır -> uygula / aday bırak.

Hedefler: ana portföy, izleme listesi ve model portföy hisseleri (BIST) ile Portföyüm ABD hisseleri. En az iki
kaynağın doğruladığı bölünme (`AUTO`) ayar açıksa (`splits.auto_apply`, varsayılan açık) `SplitApplier` ile
uygulanır; tek kaynaklı BIST olayı kurumsal aksiyon adayı olarak kaydedilir (Ayarlar > Kurumsal Aksiyonlar),
tek kaynaklı varlık olayı yalnızca sonuçta raporlanır.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import List, NamedTuple, Optional

from src.application.services.corporate_actions.split_applier import SplitApplier
from src.application.services.corporate_actions.tracked_stocks import tracked_stock_ids
from src.domain.market_clock import market_today
from src.domain.models.asset import AssetClass
from src.domain.models.corporate_action import ActionType
from src.domain.models.corporate_action_candidate import CandidateDiscoveryData, CorporateActionCandidate
from src.domain.models.split_event import SplitEvent, SplitEventStatus
from src.domain.models.split_signal import SplitDecision, SplitDecisionKind
from src.domain.ports.services.i_split_signal_provider import ISplitSignalProvider, SplitTarget
from src.domain.split_consensus import AppliedSplit, match_signals
from src.domain.ticker import to_yf_symbol

logger = logging.getLogger(__name__)

AUTO_APPLY_SETTING = "splits.auto_apply"
DEFAULT_LOOKBACK_DAYS = 400
CANDIDATE_SOURCE = "SPLIT_AUTO"


class SplitAutomationDeps(NamedTuple):
    signal_source: ISplitSignalProvider
    applier: SplitApplier
    ledger_repo: object          # ISplitLedgerRepository
    stock_repo: object
    corporate_action_repo: object
    candidate_repo: object
    settings_repo: object = None
    ledger_reader: object = None   # ILedgerReader: ana + model portföy işlemleri
    watchlist_repo: object = None
    asset_repo: object = None


@dataclass
class SplitAutomationResult:
    applied: List[SplitEvent] = field(default_factory=list)
    candidates: List[SplitDecision] = field(default_factory=list)
    already_applied: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        return ", ".join(f"{e.ticker} {e.multiplier.normalize()}:1" for e in self.applied)


class SplitAutomationService:
    def __init__(self, deps: SplitAutomationDeps) -> None:
        self._d = deps

    # ---- ayar --------------------------------------------------------------------------
    def auto_apply_enabled(self) -> bool:
        if self._d.settings_repo is None:
            return True
        value = self._d.settings_repo.get(AUTO_APPLY_SETTING)
        return value is None or value.strip().lower() not in ("0", "false", "hayir", "no")

    def set_auto_apply(self, enabled: bool) -> None:
        if self._d.settings_repo is not None:
            self._d.settings_repo.set(AUTO_APPLY_SETTING, "1" if enabled else "0")

    # ---- tarama ------------------------------------------------------------------------
    def run(self, since: Optional[date] = None) -> SplitAutomationResult:
        result = SplitAutomationResult()
        targets = self._targets()
        if not targets:
            return result
        start = since or market_today() - timedelta(days=DEFAULT_LOOKBACK_DAYS)
        signals = self._d.signal_source.fetch_signals(targets, start)
        by_key = {t.key.upper(): t for t in targets}
        auto = self.auto_apply_enabled()
        for decision in match_signals(signals, self._applied_splits()):
            target = by_key.get(decision.ticker)
            if target is None:
                continue
            self._handle(decision, target, auto, result)
        logger.info("Bölünme otomasyonu: %d uygulandı, %d aday, %d zaten uygulanmış, %d hata",
                    len(result.applied), len(result.candidates), result.already_applied, len(result.errors))
        return result

    def _handle(self, decision: SplitDecision, target: SplitTarget, auto: bool, result: SplitAutomationResult) -> None:
        if decision.kind == SplitDecisionKind.ALREADY_APPLIED:
            result.already_applied += 1
            return
        if decision.kind == SplitDecisionKind.AUTO and auto:
            try:
                result.applied.append(self._d.applier.apply(decision, target, auto_applied=True))
                return
            except Exception as exc:  # uygulanamayan olay aday olarak kullanıcıya bırakılır
                logger.warning("Bölünme uygulanamadı (%s %s): %s", decision.ticker, decision.ex_date, exc, exc_info=True)
                result.errors.append(f"{decision.ticker} {decision.ex_date:%d.%m.%Y}: {exc}")
        result.candidates.append(decision)
        self._save_candidate(decision, target)

    def revert(self, event_id: int) -> SplitEvent:
        return self._d.applier.revert(event_id)

    def list_events(self) -> List[SplitEvent]:
        return self._d.ledger_repo.list_events()

    # ---- yardımcılar -------------------------------------------------------------------
    def _targets(self) -> List[SplitTarget]:
        ids = tracked_stock_ids(self._d.ledger_reader, self._d.watchlist_repo)
        ticker_map = self._d.stock_repo.get_ticker_map_for_stock_ids(sorted(ids)) if ids else {}
        targets = [SplitTarget(t.upper(), to_yf_symbol(t), stock_id=sid) for sid, t in sorted(ticker_map.items())]
        if self._d.asset_repo is not None:
            targets += [
                SplitTarget(a.symbol.upper(), a.yf_symbol, asset_id=a.id)
                for a in self._d.asset_repo.list_assets(active_only=False)
                if a.asset_class == AssetClass.US_STOCK and a.id is not None
            ]
        return targets

    def _applied_splits(self) -> List[AppliedSplit]:
        applied: List[AppliedSplit] = [
            (e.ticker, e.ex_date, e.multiplier)
            for e in self._d.ledger_repo.list_events() if e.status == SplitEventStatus.APPLIED
        ]
        ticker_by_id = {s.id: s.ticker for s in self._d.stock_repo.get_all_stocks() if s.id is not None}
        for action in self._d.corporate_action_repo.get_all():
            if action.applied and action.action_type == ActionType.BEDELSIZ and action.stock_id in ticker_by_id:
                applied.append((ticker_by_id[action.stock_id], action.ex_date, Decimal("1") + action.ratio))
        return applied

    def _save_candidate(self, decision: SplitDecision, target: SplitTarget) -> None:
        if target.stock_id is None or decision.multiplier <= 1:
            return  # varlık defteri ve ters bölünme için mevcut aday akışı yok; sonuçta raporlanır
        sources = ",".join(s.value for s in decision.sources)
        candidate = CorporateActionCandidate.discovered(CandidateDiscoveryData(
            ticker=decision.ticker, source=CANDIDATE_SOURCE,
            source_disclosure_id=f"{decision.ticker}:{decision.ex_date.isoformat()}:{decision.multiplier.normalize()}",
            action_type=ActionType.BEDELSIZ, ratio=decision.bedelsiz_ratio, ex_date=decision.ex_date,
            stock_id=target.stock_id, confidence=Decimal("0.50"),
            parse_notes=f"Tek kaynaklı bölünme sinyali ({sources}); onay gerekir",
        ))
        try:
            self._d.candidate_repo.upsert_discovered([candidate])
        except Exception as exc:
            logger.warning("Bölünme adayı kaydedilemedi (%s): %s", decision.ticker, exc, exc_info=True)

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Iterable, Sequence

from src.domain.models.corporate_action import CorporateAction, ActionType
from src.domain.models.corporate_action_candidate import (
    CorporateActionCandidate,
    CorporateActionCandidateStatus,
)
from src.domain.ports.repositories.i_corporate_action_candidate_repo import (
    ICorporateActionCandidateRepository,
)
from src.domain.ports.repositories.i_corporate_action_repo import ICorporateActionRepository
from src.domain.ports.repositories.i_model_portfolio_repo import IModelPortfolioRepository
from src.domain.ports.repositories.i_portfolio_repo import IPortfolioRepository
from src.domain.ports.repositories.i_stock_repo import IStockRepository
from src.domain.ports.repositories.i_watchlist_repo import IWatchlistRepository
from src.domain.ports.services.i_corporate_action_provider import (
    CorporateActionProviderUnavailable,
    ICorporateActionProvider,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CorporateActionDiscoveryResult:
    fetched_count: int
    saved_count: int
    skipped_applied_count: int
    candidates: list[CorporateActionCandidate]
    errors: list[str] = field(default_factory=list)
    source_unavailable: bool = False


class CorporateActionDiscoveryService:
    def __init__(
        self,
        *,
        provider: ICorporateActionProvider,
        candidate_repo: ICorporateActionCandidateRepository,
        stock_repo: IStockRepository,
        action_repo: ICorporateActionRepository,
        portfolio_repo: IPortfolioRepository | None = None,
        watchlist_repo: IWatchlistRepository | None = None,
        model_portfolio_repo: IModelPortfolioRepository | None = None,
    ) -> None:
        self._provider = provider
        self._candidate_repo = candidate_repo
        self._stock_repo = stock_repo
        self._action_repo = action_repo
        self._portfolio_repo = portfolio_repo
        self._watchlist_repo = watchlist_repo
        self._model_portfolio_repo = model_portfolio_repo

    def discover(
        self,
        tickers: Sequence[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> CorporateActionDiscoveryResult:
        target_tickers = list(tickers or self._target_tickers())
        if not target_tickers:
            return CorporateActionDiscoveryResult(0, 0, 0, [])

        try:
            fetched = self._provider.fetch_candidates(target_tickers, start_date, end_date)
        except CorporateActionProviderUnavailable as exc:
            message = str(exc) or "KAP/MKK kaynagi gecici olarak okunamadi."
            logger.warning("Corporate action discovery source unavailable: %s", message)
            return CorporateActionDiscoveryResult(
                0,
                0,
                0,
                [],
                errors=[message],
                source_unavailable=True,
            )

        prepared = [self._prepare_candidate(candidate) for candidate in fetched]
        filtered = []
        skipped_applied = 0
        for candidate in prepared:
            if self._matches_applied_action(candidate):
                skipped_applied += 1
                continue
            filtered.append(candidate)

        saved = self._candidate_repo.upsert_discovered(filtered)
        return CorporateActionDiscoveryResult(
            fetched_count=len(fetched),
            saved_count=len(saved),
            skipped_applied_count=skipped_applied,
            candidates=saved,
        )

    def reviewable_candidates(self) -> list[CorporateActionCandidate]:
        return self._candidate_repo.get_by_statuses(
            [
                CorporateActionCandidateStatus.READY,
                CorporateActionCandidateStatus.NEEDS_REVIEW,
                CorporateActionCandidateStatus.DISCOVERED,
                CorporateActionCandidateStatus.APPROVED,
            ]
        )

    def _prepare_candidate(self, candidate: CorporateActionCandidate) -> CorporateActionCandidate:
        stock = self._stock_repo.get_stock_by_ticker(candidate.ticker)
        stock_id = stock.id if stock is not None else None
        status = CorporateActionCandidate.resolve_status(
            action_type=candidate.action_type,
            stock_id=stock_id,
            ratio=candidate.ratio,
            ex_date=candidate.ex_date,
            subscription_price=candidate.subscription_price,
        )
        return CorporateActionCandidate(
            id=candidate.id,
            ticker=candidate.ticker,
            stock_id=stock_id,
            source=candidate.source,
            source_disclosure_id=candidate.source_disclosure_id,
            source_url=candidate.source_url,
            action_type=candidate.action_type,
            status=status,
            ratio=candidate.ratio,
            subscription_price=candidate.subscription_price,
            announcement_date=candidate.announcement_date,
            ex_date=candidate.ex_date,
            confidence=candidate.confidence,
            raw_payload_json=candidate.raw_payload_json,
            parse_notes=candidate.parse_notes,
            created_at=candidate.created_at,
            updated_at=candidate.updated_at,
        )

    def _matches_applied_action(self, candidate: CorporateActionCandidate) -> bool:
        if candidate.stock_id is None or candidate.ratio is None or candidate.ex_date is None:
            return False
        for action in self._action_repo.get_by_stock(candidate.stock_id):
            if _same_action(candidate, action) and action.applied:
                return True
        return False

    def _stock_ids_from_portfolio(self) -> set:
        if self._portfolio_repo is None:
            return set()
        return {int(sid) for sid in self._portfolio_repo.get_all_stock_ids_in_portfolio()}

    def _stock_ids_from_watchlists(self) -> set:
        if self._watchlist_repo is None:
            return set()
        ids: set = set()
        for watchlist in self._watchlist_repo.get_all_watchlists():
            if watchlist.id is None:
                continue
            ids.update(item.stock_id for item in self._watchlist_repo.get_items_by_watchlist_id(watchlist.id))
        return ids

    def _stock_ids_from_model_portfolios(self) -> set:
        if self._model_portfolio_repo is None:
            return set()
        ids: set = set()
        for portfolio in self._model_portfolio_repo.get_all_model_portfolios():
            if portfolio.id is None:
                continue
            trades = self._model_portfolio_repo.get_trades_by_portfolio_id(portfolio.id)
            ids.update(trade.stock_id for trade in trades)
        return ids

    def _target_tickers(self) -> list[str]:
        stock_ids = (
            self._stock_ids_from_portfolio()
            | self._stock_ids_from_watchlists()
            | self._stock_ids_from_model_portfolios()
        )
        if not stock_ids:
            return []
        ticker_map = self._stock_repo.get_ticker_map_for_stock_ids(sorted(stock_ids))
        return sorted({ticker.upper() for ticker in ticker_map.values()})


def _same_action(candidate: CorporateActionCandidate, action: CorporateAction) -> bool:
    if candidate.action_type != action.action_type:
        return False
    if candidate.ex_date != action.ex_date:
        return False
    if candidate.ratio is None:
        return False
    if _quant(candidate.ratio, "0.00000001") != _quant(action.ratio, "0.00000001"):
        return False
    if candidate.action_type == ActionType.BEDELLI:
        if candidate.subscription_price is None or action.subscription_price is None:
            return False
        return _quant(candidate.subscription_price, "0.0001") == _quant(action.subscription_price, "0.0001")
    return True


def _quant(value: Decimal, places: str) -> Decimal:
    return value.quantize(Decimal(places))

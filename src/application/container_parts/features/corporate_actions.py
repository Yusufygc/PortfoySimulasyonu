"""Kurumsal aksiyonlar: sermaye artırımı, KAP adayları, piyasa geçmişi düzeltmeleri, otomatik bölünme."""
from __future__ import annotations

from src.application.container_parts.features._context import BuildContext
from src.application.services.corporate_actions.candidate_discovery_service import (
    CandidateDiscoveryDeps,
    CorporateActionDiscoveryService,
)
from src.application.services.corporate_actions.candidate_review_service import CorporateActionCandidateReviewService
from src.application.services.corporate_actions.corporate_action_service import CorporateActionService
from src.application.services.corporate_actions.market_action_service import MarketCorporateActionService
from src.application.services.corporate_actions.price_adjustment_service import CorporateActionPriceAdjustmentService
from src.application.services.corporate_actions.split_applier import (
    CorporateActionSplitAdapter,
    SplitApplier,
    SplitApplierDeps,
)
from src.application.services.corporate_actions.split_automation_service import (
    SplitAutomationDeps,
    SplitAutomationService,
)
from src.application.services.corporate_actions.split_signal_sources import (
    CompositeSplitSignalSource,
    KapSplitSignalSource,
    PriceBreakSplitSignalSource,
)
from src.infrastructure.corporate_actions import KapMkkCorporateActionProvider
from src.infrastructure.corporate_actions.yahoo_split_provider import YahooSplitProvider

PROVIDES = (
    "market_corporate_action_service", "corporate_action_service", "corporate_action_discovery_service",
    "corporate_action_candidate_review_service", "split_automation_service",
)


def _split_applier(r, market_action_service, projection) -> SplitApplier:
    """Tek uygulayıcı: otomatik bölünme ve kullanıcının onayladığı bedelsiz aynı yoldan uygulanır."""
    return SplitApplier(SplitApplierDeps(
        ledger_repo=r.split_ledger_repo, price_repo=r.price_repo, corporate_action_repo=r.corporate_action_repo,
        market_action_service=market_action_service, projection=projection,
    ))


def _split_automation(r, applier: SplitApplier) -> SplitAutomationService:
    signal_source = CompositeSplitSignalSource([
        YahooSplitProvider(),
        KapSplitSignalSource(KapMkkCorporateActionProvider()),
        PriceBreakSplitSignalSource(r.market_history_repo, r.price_repo),
    ])
    return SplitAutomationService(SplitAutomationDeps(
        signal_source=signal_source, applier=applier, ledger_repo=r.split_ledger_repo, stock_repo=r.stock_repo,
        corporate_action_repo=r.corporate_action_repo, candidate_repo=r.corporate_action_candidate_repo,
        settings_repo=getattr(r, "app_settings_repo", None), ledger_reader=r.ledger_reader,
        watchlist_repo=r.watchlist_repo,
        asset_repo=getattr(r, "asset_repo", None),
    ))


def build(ctx: BuildContext) -> dict:
    r = ctx.repositories
    market_action_service = MarketCorporateActionService(history_repo=r.market_history_repo, action_repo=r.market_action_repo)
    projection = ctx.services["price_projection_service"]
    price_adjustment = CorporateActionPriceAdjustmentService(
        action_repo=r.corporate_action_repo, price_repo=r.price_repo, stock_repo=r.stock_repo,
        market_action_service=market_action_service, projection=projection,
    )
    applier = _split_applier(r, market_action_service, projection)
    ctx.internal["split_applier"] = applier
    corporate_action_service = CorporateActionService(
        action_repo=r.corporate_action_repo, portfolio_repo=r.portfolio_repo,
        trade_adjustment_repo=getattr(r, "trade_adjustment_repo", None), price_adjustment_service=price_adjustment,
        split_applier=CorporateActionSplitAdapter(applier, r.stock_repo),
    )
    return {
        "market_corporate_action_service": market_action_service,
        "corporate_action_service": corporate_action_service,
        "corporate_action_discovery_service": CorporateActionDiscoveryService(deps=CandidateDiscoveryDeps(
            provider=KapMkkCorporateActionProvider(), candidate_repo=r.corporate_action_candidate_repo,
            stock_repo=r.stock_repo, action_repo=r.corporate_action_repo, ledger_reader=r.ledger_reader,
            watchlist_repo=r.watchlist_repo,
        )),
        "corporate_action_candidate_review_service": CorporateActionCandidateReviewService(
            candidate_repo=r.corporate_action_candidate_repo, corporate_action_service=corporate_action_service,
        ),
        "split_automation_service": _split_automation(r, applier),
    }

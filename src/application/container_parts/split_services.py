"""Otomatik bölünme servisinin kurulumu (sinyal kaynakları, uygulayıcı, orkestrasyon)."""
from __future__ import annotations

from src.application.services.corporate_actions.split_applier import SplitApplier, SplitApplierDeps
from src.application.services.corporate_actions.split_automation_service import (
    SplitAutomationDeps,
    SplitAutomationService,
)
from src.application.services.corporate_actions.split_signal_sources import (
    CompositeSplitSignalSource,
    KapSplitSignalSource,
    PriceBreakSplitSignalSource,
)
from src.infrastructure.corporate_actions.kap_mkk_provider import KapMkkCorporateActionProvider
from src.infrastructure.corporate_actions.yahoo_split_provider import YahooSplitProvider


def build_split_automation_service(repositories, market_action_service) -> SplitAutomationService:
    ledger_repo = repositories.split_ledger_repo
    signal_source = CompositeSplitSignalSource([
        YahooSplitProvider(),
        KapSplitSignalSource(KapMkkCorporateActionProvider()),
        PriceBreakSplitSignalSource(repositories.market_history_repo, repositories.price_repo),
    ])
    applier = SplitApplier(SplitApplierDeps(
        ledger_repo=ledger_repo,
        price_repo=repositories.price_repo,
        corporate_action_repo=repositories.corporate_action_repo,
        market_action_service=market_action_service,
    ))
    return SplitAutomationService(SplitAutomationDeps(
        signal_source=signal_source,
        applier=applier,
        ledger_repo=ledger_repo,
        stock_repo=repositories.stock_repo,
        corporate_action_repo=repositories.corporate_action_repo,
        candidate_repo=repositories.corporate_action_candidate_repo,
        settings_repo=getattr(repositories, "app_settings_repo", None),
        portfolio_repo=repositories.portfolio_repo,
        watchlist_repo=repositories.watchlist_repo,
        model_portfolio_repo=repositories.model_portfolio_repo,
        asset_repo=getattr(repositories, "asset_repo", None),
    ))

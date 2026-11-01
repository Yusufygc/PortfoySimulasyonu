"""Varlık defteri servisi ve repository'leri uygulama container'ında kayıtlıdır (geçici veritabanıyla)."""
from __future__ import annotations

from src.application.container import AppContainer
from src.application.services.assets.asset_ledger_service import AssetLedgerService


def test_container_exposes_asset_ledger_service_and_repositories():
    container = AppContainer()

    assert isinstance(container.asset_ledger_service, AssetLedgerService)
    for name in ("asset_repo", "asset_trade_repo", "asset_price_repo", "fx_rate_repo"):
        assert getattr(container, name) is not None
    assert container.asset_ledger_service.get_ledger().open_positions() is not None


def test_container_exposes_news_services_with_seeded_default_sources():
    from src.application.services.news.news_service import NewsService

    container = AppContainer()

    assert isinstance(container.news_service, NewsService)
    sources = {s.source_id: s for s in container.news_service.list_sources()}
    assert {"kap", "yahoo_rss", "google_news", "rss:aa_ekonomi"} <= set(sources)
    assert container.news_target_service.get_targets() is not None


def test_unified_summary_reads_real_database_without_network():
    from src.domain.models.unified_portfolio import UnifiedSummary

    container = AppContainer()

    summary = container.unified_portfolio_service.get_summary()

    assert isinstance(summary, UnifiedSummary)
    assert summary.total_value_try >= summary.cash_try
    if summary.slices:
        assert abs(sum(s.weight_pct for s in summary.slices) - 100) < 1

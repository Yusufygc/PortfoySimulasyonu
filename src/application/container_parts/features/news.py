"""Haber akışı ve haber hedefleri."""
from __future__ import annotations

from src.application.container_parts.features._context import BuildContext
from src.application.services.news.news_service import NewsService
from src.application.services.news.news_target_service import NewsTargetService
from src.infrastructure.news.default_sources import default_news_sources
from src.infrastructure.news.news_file_cache import JsonFileNewsCache
from src.infrastructure.news.provider_factory import NewsProviderFactory

PROVIDES = ("news_service", "news_target_service")


def build(ctx: BuildContext) -> dict:
    r, m, s = ctx.repositories, ctx.market_clients, ctx.services
    return {
        "news_service": NewsService(
            source_repo=r.news_source_repo,
            provider_factory=NewsProviderFactory(lambda ticker: m.kap_shareholder_provider.resolve_member_oid(ticker)[0]),
            cache=JsonFileNewsCache(),
            default_sources=default_news_sources,
        ),
        "news_target_service": NewsTargetService(
            portfolio_service=s["portfolio_service"], stock_lookup_service=s["stock_lookup_service"],
            asset_ledger_service=s["asset_ledger_service"], watchlist_service=s["watchlist_service"],
        ),
    }

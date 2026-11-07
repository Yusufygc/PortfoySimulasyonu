"""Piyasa verisi: fiyat sağlığı, canlı fiyat, backfill, güncel fiyat çözümü, hisse sorgusu, senkron, gösterge şeridi."""
from __future__ import annotations

from src.application.container_parts.features._context import BuildContext
from src.application.services.market.current_price_resolver import CurrentPriceResolver
from src.application.services.market.live_price_refresh_service import LivePriceRefreshService
from src.application.services.market.market_indicators_service import MarketIndicatorsService
from src.application.services.market.price_data_health_service import PriceDataHealthService, PriceHealthServiceDeps
from src.application.services.market.stock_lookup_service import StockLookupService
from src.application.services.market_data.market_data_sync_service import MarketDataSyncService
from src.application.services.simulation.backfill_service import BackfillService
from src.infrastructure.calendar.bist_holiday_provider import BistHolidayProvider

PROVIDES = (
    "price_data_health_service", "live_price_refresh_service", "backfill_service", "current_price_resolver",
    "stock_lookup_service", "market_indicators_service", "market_data_sync_service",
)


def _watchlist_stock_ids(watchlist_repo) -> set:
    """Tüm izleme listelerindeki hisse kimlikleri (canlı fiyat yenilemesine dahil edilir)."""
    return {
        item.stock_id
        for watchlist in watchlist_repo.get_all_watchlists()
        for item in watchlist_repo.get_items_by_watchlist_id(watchlist.id)
    }


def build(ctx: BuildContext) -> dict:
    r, m = ctx.repositories, ctx.market_clients
    health = PriceDataHealthService(
        deps=PriceHealthServiceDeps(
            stock_repo=r.stock_repo, price_repo=r.price_repo, market_data_client=m.market_client,
            portfolio_repo=r.portfolio_repo, model_portfolio_repo=r.model_portfolio_repo,
            corporate_action_repo=r.corporate_action_repo,
        ),
        holiday_provider=BistHolidayProvider(),
    )
    indicator_provider = getattr(m, "market_indicator_provider", None)
    return {
        "price_data_health_service": health,
        "live_price_refresh_service": LivePriceRefreshService(
            stock_repo=r.stock_repo, price_lookup_service=m.price_lookup_service, price_data_health_service=health,
            latest_price_repo=r.latest_price_repo, extra_stock_ids_provider=lambda: _watchlist_stock_ids(r.watchlist_repo),
        ),
        "backfill_service": BackfillService(
            stock_repo=r.stock_repo, price_repo=r.price_repo, market_data_client=m.market_client,
            corporate_action_repo=r.corporate_action_repo,
        ),
        "current_price_resolver": CurrentPriceResolver(
            latest_price_repo=r.latest_price_repo, price_repo=r.price_repo, session_service=m.bist_market_session_service,
        ),
        "stock_lookup_service": StockLookupService(
            stock_repo=r.stock_repo, price_repo=r.price_repo, latest_price_repo=r.latest_price_repo,
            market_history_repo=r.market_history_repo, price_lookup_service=m.price_lookup_service,
        ),
        "market_indicators_service": MarketIndicatorsService(indicator_provider) if indicator_provider is not None else None,
        "market_data_sync_service": MarketDataSyncService(
            r.market_history_store, getattr(m, "market_bar_downloader", None), trading_calendar=m.trading_calendar,
            stock_repo=r.stock_repo, projection=ctx.services["price_projection_service"],
            market_action_service=ctx.services["market_corporate_action_service"],
            portfolio_action_repo=r.corporate_action_repo,
        ),
    }

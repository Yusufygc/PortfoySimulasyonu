"""Tek fiyat kaynağı: DuckDB piyasa geçmişinden SQLite `daily_prices` yansıması."""
from __future__ import annotations

from src.application.container_parts.features._context import BuildContext
from src.application.services.market_data.market_price_refresher import MarketPriceRefresher
from src.application.services.market_data.price_projection_service import PriceProjectionService
from src.infrastructure.market_data.bar_quality import is_ghost_bar

PROVIDES = ("price_projection_service", "market_price_refresher")


def _ghost(bar) -> bool:
    return is_ghost_bar(bar.price_date, (bar.open_price, bar.high_price, bar.low_price, bar.close_price, bar.volume))


def build(ctx: BuildContext) -> dict:
    r, m = ctx.repositories, ctx.market_clients
    projection = PriceProjectionService(r.market_history_repo, r.price_repo, r.stock_repo, _ghost)
    return {
        "price_projection_service": projection,
        "market_price_refresher": MarketPriceRefresher(
            getattr(m, "market_bar_downloader", None), r.market_history_store, projection,
        ),
    }

"""Portföyüm: BIST dışı varlık defteri, kurlar, birleşik portföy, döviz çevirme, pozisyon sorgusu, varlık grafiği."""
from __future__ import annotations

from src.application.container_parts.features._context import BuildContext
from src.application.container_parts.features.analysis import unified_series_builder
from src.application.services.analysis.unified_return_service import UnifiedReturnService
from src.application.services.assets.asset_chart_service import AssetChartService
from src.application.services.assets.asset_holdings_reader import AssetHoldingsReader
from src.application.services.assets.asset_ledger_service import AssetLedgerService
from src.application.services.assets.asset_price_refresh_service import AssetPriceRefreshService
from src.application.services.assets.bist_holdings_reader import BistHoldingsReader
from src.application.services.assets.fx_rate_service import FxRateService
from src.application.services.assets.unified_portfolio_service import UnifiedPortfolioService
from src.application.services.planning.unified_optimization_service import UnifiedOptimizationService
from src.application.services.portfolio.fx_conversion_service import FxConversionService
from src.application.services.portfolio.position_query_service import PositionQueryService

PROVIDES = (
    "asset_ledger_service", "asset_price_refresh_service", "fx_rate_service", "unified_portfolio_service",
    "unified_return_service", "unified_optimization_service", "fx_conversion_service", "position_query_service",
    "asset_chart_service",
)


def build(ctx: BuildContext) -> dict:
    r, m, s = ctx.repositories, ctx.market_clients, ctx.services
    ledger = AssetLedgerService(
        asset_repo=r.asset_repo, trade_repo=r.asset_trade_repo, symbol_verifier=m.asset_price_provider,
        fee_service=s["fee_settings_service"], cash_pool=s["cash_pool_service"],
    )
    fx_rates = FxRateService(provider=m.asset_price_provider, repo=r.fx_rate_repo)
    bist_reader = BistHoldingsReader(s["portfolio_service"], s["stock_lookup_service"], s["current_price_resolver"])
    unified = UnifiedPortfolioService(
        bist_reader=bist_reader, asset_reader=AssetHoldingsReader(ledger, r.asset_price_repo, fx_rates),
        fx_rate_service=fx_rates, cash_pool=s["cash_pool_service"],
    )
    return {
        "asset_ledger_service": ledger,
        "asset_price_refresh_service": AssetPriceRefreshService(
            asset_repo=r.asset_repo, price_repo=r.asset_price_repo, provider=m.asset_price_provider,
        ),
        "fx_rate_service": fx_rates,
        "unified_portfolio_service": unified,
        "unified_return_service": UnifiedReturnService(unified_series_builder(r)),
        "unified_optimization_service": UnifiedOptimizationService(
            unified, s["optimization_service"], r.asset_repo, r.asset_price_repo, r.fx_rate_repo,
        ),
        "fx_conversion_service": FxConversionService(r.fx_conversion_repo, s["cash_pool_service"], fx_rates),
        "position_query_service": PositionQueryService(
            bist_reader=bist_reader, model_portfolio_service=s["model_portfolio_service"],
            stock_lookup_service=s["stock_lookup_service"], price_resolver=s["current_price_resolver"],
        ),
        "asset_chart_service": AssetChartService(ledger, r.asset_price_repo),
    }

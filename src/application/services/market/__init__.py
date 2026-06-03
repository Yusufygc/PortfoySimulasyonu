from .price_data_health_service import (
    PriceDataHealthReport,
    PriceDataScopeOption,
    PriceDataHealthService,
    PriceDataUpdateResult,
    StockPriceHealthRow,
)
from .live_price_refresh_service import LivePriceRefreshResult, LivePriceRefreshService
from .bist_market_session_service import BistMarketSessionService, MarketSessionStatus

__all__ = [
    "PriceLookupResult",
    "PriceLookupService",
    "PriceDataHealthReport",
    "PriceDataScopeOption",
    "PriceDataHealthService",
    "PriceDataUpdateResult",
    "StockPriceHealthRow",
    "LivePriceRefreshResult",
    "LivePriceRefreshService",
    "BistMarketSessionService",
    "MarketSessionStatus",
]


def __getattr__(name):
    if name in {"PriceLookupResult", "PriceLookupService"}:
        from .price_lookup_service import PriceLookupResult, PriceLookupService

        return {"PriceLookupResult": PriceLookupResult, "PriceLookupService": PriceLookupService}[name]
    raise AttributeError(name)

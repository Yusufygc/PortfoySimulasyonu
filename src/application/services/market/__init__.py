from .price_data_health_service import (
    PriceDataHealthReport,
    PriceDataHealthService,
    PriceDataUpdateResult,
    StockPriceHealthRow,
)
from .bist_market_session_service import BistMarketSessionService, MarketSessionStatus

__all__ = [
    "PriceLookupResult",
    "PriceLookupService",
    "PriceDataHealthReport",
    "PriceDataHealthService",
    "PriceDataUpdateResult",
    "StockPriceHealthRow",
    "BistMarketSessionService",
    "MarketSessionStatus",
]


def __getattr__(name):
    if name in {"PriceLookupResult", "PriceLookupService"}:
        from .price_lookup_service import PriceLookupResult, PriceLookupService

        return {"PriceLookupResult": PriceLookupResult, "PriceLookupService": PriceLookupService}[name]
    raise AttributeError(name)

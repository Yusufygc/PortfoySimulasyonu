from __future__ import annotations

from dataclasses import dataclass

from src.application.services.database import DatabaseIntegrityService
from src.application.services.market.bist_market_session_service import BistMarketSessionService
from src.application.services.market.price_lookup_service import PriceLookupService
from src.infrastructure.market_data.evds_client import EvdsClient
from src.infrastructure.market_data.yfinance_client import YFinanceMarketDataClient


@dataclass(frozen=True)
class MarketClientSet:
    market_client: YFinanceMarketDataClient
    evds_client: EvdsClient
    price_lookup_service: PriceLookupService
    bist_market_session_service: BistMarketSessionService
    db_integrity_service: DatabaseIntegrityService


def build_market_clients(conn_provider) -> MarketClientSet:
    return MarketClientSet(
        market_client=YFinanceMarketDataClient(),
        evds_client=EvdsClient(),
        price_lookup_service=PriceLookupService(),
        bist_market_session_service=BistMarketSessionService(),
        db_integrity_service=DatabaseIntegrityService(conn_provider),
    )

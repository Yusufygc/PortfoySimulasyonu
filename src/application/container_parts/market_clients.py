from __future__ import annotations

from dataclasses import dataclass

from src.application.services.database import DatabaseIntegrityService
from src.application.services.market.bist_market_session_service import BistMarketSessionService
from src.application.services.market.price_lookup_service import PriceLookupService
from src.infrastructure.market_data.evds_client import EvdsClient
from src.infrastructure.calendar.bist_trading_calendar_provider import BistTradingCalendarProvider
from src.infrastructure.market_data.evds_tufe_provider import EvdsTufeProvider
from src.infrastructure.market_data.isyatirim_provider import IsyatirimProvider
from src.infrastructure.market_data.yfinance_client import YFinanceMarketDataClient
from src.infrastructure.market_data.yfinance_optimization_market_data_provider import (
    YFinanceOptimizationMarketDataProvider,
)
from src.infrastructure.market_data.yfinance_price_lookup_provider import YFinancePriceLookupProvider
from src.infrastructure.market_data.yfinance_valuation_provider import YFinanceValuationProvider


@dataclass(frozen=True)
class MarketClientSet:
    market_client: YFinanceMarketDataClient
    optimization_market_data_provider: YFinanceOptimizationMarketDataProvider
    trading_calendar: BistTradingCalendarProvider
    evds_client: EvdsClient
    price_lookup_service: PriceLookupService
    bist_market_session_service: BistMarketSessionService
    db_integrity_service: DatabaseIntegrityService
    isyatirim_provider: IsyatirimProvider
    evds_tufe_provider: EvdsTufeProvider
    yfinance_valuation_provider: YFinanceValuationProvider


def build_market_clients(conn_provider) -> MarketClientSet:
    trading_calendar = BistTradingCalendarProvider()
    evds_client      = EvdsClient()
    return MarketClientSet(
        market_client=YFinanceMarketDataClient(),
        optimization_market_data_provider=YFinanceOptimizationMarketDataProvider(),
        trading_calendar=trading_calendar,
        evds_client=evds_client,
        price_lookup_service=PriceLookupService(provider=YFinancePriceLookupProvider()),
        bist_market_session_service=BistMarketSessionService(trading_calendar=trading_calendar),
        db_integrity_service=DatabaseIntegrityService(conn_provider),
        isyatirim_provider=IsyatirimProvider(),
        evds_tufe_provider=EvdsTufeProvider(evds_client=evds_client),
        yfinance_valuation_provider=YFinanceValuationProvider(),
    )

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from src.application.services.market.bist_market_session_service import BistMarketSessionService
from src.application.services.market.price_lookup_service import PriceLookupService
from src.infrastructure.market_data.evds_client import EvdsClient
from src.infrastructure.calendar.bist_trading_calendar_provider import BistTradingCalendarProvider
from src.infrastructure.market_data.evds_tufe_provider import EvdsTufeProvider
from src.infrastructure.market_data.isyatirim_provider import IsyatirimProvider
from src.infrastructure.market_data.yfinance_client import YFinanceMarketDataClient
from src.infrastructure.market_data.yfinance_indicator_provider import YFinanceIndicatorProvider
from src.infrastructure.market_data.yfinance_optimization_market_data_provider import (
    YFinanceOptimizationMarketDataProvider,
)
from src.infrastructure.market_data.duckdb_optimization_market_data_provider import (
    DuckDBOptimizationMarketDataProvider,
)
from src.infrastructure.market_data.yfinance_price_lookup_provider import YFinancePriceLookupProvider
from src.infrastructure.market_data.yfinance_valuation_provider import YFinanceValuationProvider
from src.infrastructure.corporate_actions.kap_shareholder_provider import KapShareholderProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MarketClientSet:
    market_client: YFinanceMarketDataClient
    optimization_market_data_provider: object
    trading_calendar: BistTradingCalendarProvider
    evds_client: EvdsClient
    price_lookup_service: PriceLookupService
    bist_market_session_service: BistMarketSessionService
    isyatirim_provider: IsyatirimProvider
    evds_tufe_provider: EvdsTufeProvider
    yfinance_valuation_provider: YFinanceValuationProvider
    kap_shareholder_provider: KapShareholderProvider
    market_indicator_provider: Optional[YFinanceIndicatorProvider] = field(default=None)


def build_market_clients(conn_provider) -> MarketClientSet:
    trading_calendar = BistTradingCalendarProvider()
    evds_client      = EvdsClient()
    yf_opt_provider  = YFinanceOptimizationMarketDataProvider()
    duckdb_opt_provider = DuckDBOptimizationMarketDataProvider(fallback_provider=yf_opt_provider)
    return MarketClientSet(
        market_client=YFinanceMarketDataClient(),
        optimization_market_data_provider=duckdb_opt_provider,
        trading_calendar=trading_calendar,
        evds_client=evds_client,
        price_lookup_service=PriceLookupService(provider=YFinancePriceLookupProvider()),
        bist_market_session_service=BistMarketSessionService(trading_calendar=trading_calendar),
        isyatirim_provider=IsyatirimProvider(),
        evds_tufe_provider=EvdsTufeProvider(evds_client=evds_client),
        yfinance_valuation_provider=YFinanceValuationProvider(),
        kap_shareholder_provider=KapShareholderProvider(),
        market_indicator_provider=YFinanceIndicatorProvider(),
    )

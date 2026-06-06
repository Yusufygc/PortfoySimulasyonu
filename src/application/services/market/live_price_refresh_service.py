from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List

from src.application.services.market.price_data_health_service import PRICE_SCOPE_ALL_ACTIVE
from src.application.services.market.price_lookup_service import PriceLookupService
from src.domain.models.latest_price import LatestPrice
from src.domain.ports.repositories.i_latest_price_repo import ILatestPriceRepository
from src.domain.ports.repositories.i_stock_repo import IStockRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LivePriceRefreshResult:
    scanned_count: int
    updated_count: int
    prices: Dict[int, Decimal]
    errors: List[str] = field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class LivePriceRefreshService:
    """Refresh latest/intraday prices for active positions without writing daily_prices."""

    def __init__(
        self,
        stock_repo: IStockRepository,
        price_lookup_service: PriceLookupService,
        price_data_health_service,
        latest_price_repo: ILatestPriceRepository | None = None,
    ) -> None:
        self._stock_repo = stock_repo
        self._price_lookup_service = price_lookup_service
        self._price_data_health_service = price_data_health_service
        self._latest_price_repo = latest_price_repo

    def refresh_active_prices(self, scope: str | None = PRICE_SCOPE_ALL_ACTIVE) -> LivePriceRefreshResult:
        started_at = datetime.now(timezone.utc)
        stock_ids = sorted(self._price_data_health_service.active_stock_ids(scope))
        ticker_map = self._stock_repo.get_ticker_map_for_stock_ids(stock_ids)

        prices: Dict[int, Decimal] = {}
        latest_prices: List[LatestPrice] = []
        errors: List[str] = []
        for stock_id in stock_ids:
            ticker = ticker_map.get(stock_id)
            if not ticker:
                errors.append(f"{stock_id}: ticker bulunamadi.")
                continue
            try:
                result = self._price_lookup_service.lookup_price_for_ticker(ticker)
            except Exception as exc:
                logger.warning("Live price lookup failed for %s: %s", ticker, exc)
                errors.append(f"{ticker}: {exc}")
                continue
            if result is None:
                errors.append(f"{ticker}: fiyat bulunamadi.")
                continue
            prices[stock_id] = result.price
            latest_prices.append(
                LatestPrice(
                    id=None,
                    stock_id=stock_id,
                    price=result.price,
                    as_of=result.as_of,
                    source=result.source,
                    provider="price_lookup",
                    fetched_at=datetime.now(timezone.utc),
                )
            )

        if self._latest_price_repo is not None:
            self._latest_price_repo.upsert_latest_prices(latest_prices)

        return LivePriceRefreshResult(
            scanned_count=len(stock_ids),
            updated_count=len(prices),
            prices=prices,
            errors=errors,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )

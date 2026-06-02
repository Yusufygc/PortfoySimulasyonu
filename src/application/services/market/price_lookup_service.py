from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PriceLookupResult:
    price: Decimal
    as_of: datetime
    source: str
    company_name: str | None = None
    normalized_ticker: str = ""


@dataclass(frozen=True)
class PriceLookupSnapshot:
    intraday_price: Decimal | None = None
    last_close_price: Decimal | None = None
    last_close_as_of: datetime | None = None
    company_name: str | None = None


class PriceLookupProvider(Protocol):
    def lookup(self, normalized_ticker: str) -> PriceLookupSnapshot | None:
        """Return latest known price data for an already-normalized ticker."""


class PriceLookupService:
    def __init__(self, provider: PriceLookupProvider) -> None:
        self._provider = provider

    def lookup_price_for_ticker(self, ticker: str) -> Optional[PriceLookupResult]:
        if not ticker:
            return None

        normalized_ticker = ticker.strip().upper()
        if "." not in normalized_ticker:
            normalized_ticker += ".IS"

        snapshot = self._provider.lookup(normalized_ticker)
        if snapshot is None:
            logger.warning("Price lookup failed for %s", normalized_ticker)
            return None

        if snapshot.intraday_price is not None:
            return PriceLookupResult(
                price=snapshot.intraday_price,
                as_of=datetime.now(timezone.utc),
                source="intraday",
                company_name=snapshot.company_name,
                normalized_ticker=normalized_ticker,
            )

        if snapshot.last_close_price is not None:
            return PriceLookupResult(
                price=snapshot.last_close_price,
                as_of=snapshot.last_close_as_of or datetime.now(timezone.utc),
                source="last_close",
                company_name=snapshot.company_name,
                normalized_ticker=normalized_ticker,
            )

        logger.warning("Price lookup provider returned no usable price for %s", normalized_ticker)
        return None

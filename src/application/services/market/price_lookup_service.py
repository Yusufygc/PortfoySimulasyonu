from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Iterable, Optional, Protocol

logger = logging.getLogger(__name__)


def normalize_lookup_ticker(ticker: str) -> str:
    normalized = (ticker or "").strip().upper()
    return normalized if "." in normalized else normalized + ".IS"


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

    def lookup_prices_bulk(self, tickers: Iterable[str]) -> Dict[str, PriceLookupResult]:
        """Birçok hissenin son gün içi fiyatı tek toplu istekle (sağlayıcı destekliyorsa); anahtar verilen ticker.

        `as_of` son dakika barının zamanıdır (seans dışında son seansın son barı); bulunamayan hisseler sonuçta yoktur,
        çağıran onları tekli yoldan deneyebilir.
        """
        bulk = getattr(self._provider, "lookup_intraday_bulk", None)
        by_symbol = {normalize_lookup_ticker(t): t for t in tickers if t}
        if bulk is None or not by_symbol:
            return {}
        try:
            quotes = bulk(list(by_symbol)) or {}
        except Exception as exc:
            logger.warning("Toplu fiyat sorgusu başarısız: %s", exc)
            return {}
        return {
            by_symbol[symbol]: PriceLookupResult(price=price, as_of=as_of, source="intraday", normalized_ticker=symbol)
            for symbol, (price, as_of) in quotes.items()
            if symbol in by_symbol
        }

    def lookup_price_for_ticker(self, ticker: str) -> Optional[PriceLookupResult]:
        if not ticker:
            return None

        normalized_ticker = normalize_lookup_ticker(ticker)

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

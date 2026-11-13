"""Port: Piyasa değerleme anlık veri sağlayıcı arayüzü."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


class MarketValuationUnavailable(RuntimeError):
    """Piyasa değerleme verisi alınamadığında fırlatılır."""


@runtime_checkable
class IMarketValuationProvider(Protocol):
    def get_market_snapshot(self, ticker: str) -> dict[str, Any]:
        """
        Anlık piyasa verisi.
        {"ticker", "price", "market_cap", "shares_outstanding", "currency", "error"}
        """
        ...

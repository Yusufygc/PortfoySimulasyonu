from __future__ import annotations

from decimal import Decimal
from typing import Mapping


def publish_prices_updated(event_bus, prices: Mapping[int, Decimal] | None) -> bool:
    """Publish normalized price updates through the global event bus."""
    if not prices or event_bus is None:
        return False
    event_bus.prices_updated.emit(dict(prices))
    return True

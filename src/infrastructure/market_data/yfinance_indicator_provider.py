from __future__ import annotations

import logging
from typing import Any, Optional

from src.domain.models.market_indicator import IndicatorQuote
from src.domain.ports.services.i_market_indicator_provider import IMarketIndicatorProvider

logger = logging.getLogger(__name__)

_LAST_KEYS = ("lastPrice", "last_price", "regularMarketPrice", "currentPrice")
_PREVIOUS_KEYS = ("previousClose", "previous_close", "regularMarketPreviousClose")


def _first_float(info: Any, keys) -> Optional[float]:
    for key in keys:
        try:
            value = info.get(key) if hasattr(info, "get") else getattr(info, key, None)
        except Exception:
            value = None
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number > 0:
            return number
    return None


class YFinanceIndicatorProvider(IMarketIndicatorProvider):
    def get_quote(self, symbol: str) -> Optional[IndicatorQuote]:
        from .yfinance_lock import yfinance_lock

        with yfinance_lock:
            try:
                import yfinance as yf

                info = getattr(yf.Ticker(symbol), "fast_info", None)
                if info is None:
                    return None
                last = _first_float(info, _LAST_KEYS)
                if last is None:
                    return None
                return IndicatorQuote(last=last, previous_close=_first_float(info, _PREVIOUS_KEYS))
            except Exception as exc:
                logger.debug("Gösterge alınamadı (%s): %s", symbol, exc)
                return None

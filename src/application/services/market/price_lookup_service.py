from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PriceLookupResult:
    price: Decimal
    as_of: datetime
    source: str


class PriceLookupService:
    def lookup_price_for_ticker(self, ticker: str) -> Optional[PriceLookupResult]:
        if not ticker:
            return None

        normalized_ticker = ticker.upper()
        if "." not in normalized_ticker:
            normalized_ticker += ".IS"

        try:
            yf_ticker = yf.Ticker(normalized_ticker)
        except Exception as exc:
            logger.error("YF Ticker init failed for %s: %s", normalized_ticker, exc)
            return None

        info = {}
        try:
            info = getattr(yf_ticker, "fast_info", None) or yf_ticker.info
        except Exception:
            info = {}

        if isinstance(info, dict):
            for value in (
                info.get("lastPrice"),
                info.get("last_price"),
                info.get("regularMarketPrice"),
                info.get("currentPrice"),
            ):
                if value is None:
                    continue
                try:
                    return PriceLookupResult(
                        price=Decimal(str(float(value))),
                        as_of=datetime.now(timezone.utc),
                        source="intraday",
                    )
                except Exception:
                    continue

        try:
            history = yf_ticker.history(period="5d", auto_adjust=False)
        except Exception as exc:
            logger.error("YF history failed for %s: %s", normalized_ticker, exc)
            return None

        if history is not None and not history.empty and "Close" in history:
            close_series = history["Close"].dropna()
            if not close_series.empty:
                last_ts = close_series.index[-1]
                last_price = close_series.iloc[-1]
                try:
                    as_of = (
                        last_ts.to_pydatetime().replace(tzinfo=timezone.utc)
                        if hasattr(last_ts, "to_pydatetime")
                        else datetime.now(timezone.utc)
                    )
                    return PriceLookupResult(
                        price=Decimal(str(float(last_price))),
                        as_of=as_of,
                        source="last_close",
                    )
                except Exception:
                    pass

        logger.warning("Price lookup failed for %s", normalized_ticker)
        return None


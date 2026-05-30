from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PriceLookupResult:
    price: Decimal
    as_of: datetime
    source: str
    company_name: str | None = None
    normalized_ticker: str = ""


class PriceLookupService:
    def lookup_price_for_ticker(self, ticker: str) -> Optional[PriceLookupResult]:
        if not ticker:
            return None

        normalized_ticker = ticker.strip().upper()
        if "." not in normalized_ticker:
            normalized_ticker += ".IS"

        try:
            yf_ticker = yf.Ticker(normalized_ticker)
        except Exception as exc:
            logger.error("YF Ticker init failed for %s: %s", normalized_ticker, exc)
            return None

        fast_info = {}
        try:
            fast_info = self._as_mapping(getattr(yf_ticker, "fast_info", None))
        except Exception:
            fast_info = {}

        info = {}
        try:
            info = self._as_mapping(getattr(yf_ticker, "info", None))
        except Exception:
            info = {}

        company_name = self._extract_company_name(info)
        for price_source in (fast_info, info):
            for value in (
                price_source.get("lastPrice"),
                price_source.get("last_price"),
                price_source.get("regularMarketPrice"),
                price_source.get("currentPrice"),
            ):
                if value is None:
                    continue
                try:
                    return PriceLookupResult(
                        price=Decimal(str(float(value))),
                        as_of=datetime.now(timezone.utc),
                        source="intraday",
                        company_name=company_name,
                        normalized_ticker=normalized_ticker,
                    )
                except Exception:
                    continue

        try:
            history = yf_ticker.history(period="7d", auto_adjust=False)
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
                        company_name=company_name,
                        normalized_ticker=normalized_ticker,
                    )
                except Exception:
                    pass

        logger.warning("Price lookup failed for %s", normalized_ticker)
        return None

    @staticmethod
    def _as_mapping(value: Any) -> dict:
        if isinstance(value, dict):
            return value
        if value is None:
            return {}

        result = {}
        for key in (
            "lastPrice",
            "last_price",
            "regularMarketPrice",
            "currentPrice",
            "longName",
            "shortName",
            "displayName",
        ):
            try:
                item = value.get(key) if hasattr(value, "get") else getattr(value, key, None)
            except Exception:
                item = None
            if item is not None:
                result[key] = item
        return result

    @staticmethod
    def _extract_company_name(info: dict) -> str | None:
        for key in ("longName", "shortName", "displayName"):
            value = info.get(key)
            if value:
                return str(value).strip()
        return None

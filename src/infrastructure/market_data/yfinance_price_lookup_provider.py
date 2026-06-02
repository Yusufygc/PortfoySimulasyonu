from __future__ import annotations

import logging
from datetime import timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import yfinance as yf

from src.application.services.market.price_lookup_service import PriceLookupSnapshot
from src.infrastructure.market_data._errors import MARKET_DATA_FALLBACK_ERRORS

logger = logging.getLogger(__name__)


class YFinancePriceLookupProvider:
    def lookup(self, normalized_ticker: str) -> PriceLookupSnapshot | None:
        try:
            yf_ticker = yf.Ticker(normalized_ticker)
        except MARKET_DATA_FALLBACK_ERRORS as exc:
            logger.error("YF Ticker init failed for %s: %s", normalized_ticker, exc)
            return None

        fast_info = self._safe_mapping(getattr(yf_ticker, "fast_info", None))
        info = self._safe_mapping(getattr(yf_ticker, "info", None))
        company_name = self._extract_company_name(info)

        intraday_price = self._extract_intraday_price(fast_info, info)
        if intraday_price is not None:
            return PriceLookupSnapshot(
                intraday_price=intraday_price,
                company_name=company_name,
            )

        try:
            history = yf_ticker.history(period="7d", auto_adjust=False)
        except MARKET_DATA_FALLBACK_ERRORS as exc:
            logger.error("YF history failed for %s: %s", normalized_ticker, exc)
            return None

        if history is None or history.empty or "Close" not in history:
            return None

        close_series = history["Close"].dropna()
        if close_series.empty:
            return None

        last_ts = close_series.index[-1]
        last_price = self._to_decimal(close_series.iloc[-1])
        if last_price is None:
            return None

        as_of = (
            last_ts.to_pydatetime().replace(tzinfo=timezone.utc)
            if hasattr(last_ts, "to_pydatetime")
            else None
        )
        return PriceLookupSnapshot(
            last_close_price=last_price,
            last_close_as_of=as_of,
            company_name=company_name,
        )

    def _safe_mapping(self, value: Any) -> dict:
        try:
            return self._as_mapping(value)
        except (TypeError, ValueError, KeyError, AttributeError):
            return {}

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
            except (TypeError, ValueError, KeyError, AttributeError):
                item = None
            if item is not None:
                result[key] = item
        return result

    @classmethod
    def _extract_intraday_price(cls, *sources: dict) -> Decimal | None:
        for source in sources:
            for key in ("lastPrice", "last_price", "regularMarketPrice", "currentPrice"):
                price = cls._to_decimal(source.get(key))
                if price is not None:
                    return price
        return None

    @staticmethod
    def _extract_company_name(info: dict) -> str | None:
        for key in ("longName", "shortName", "displayName"):
            value = info.get(key)
            if value:
                return str(value).strip()
        return None

    @staticmethod
    def _to_decimal(value: Any) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(float(value)))
        except (TypeError, ValueError, InvalidOperation, OverflowError):
            return None

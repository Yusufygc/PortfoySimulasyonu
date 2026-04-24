from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Optional
from uuid import uuid4

import pandas as pd

logger = logging.getLogger(__name__)


class InvestingFallbackClient:
    INVESTING_SEARCH_ALIASES = {
        "XU100.IS": {"query": "XU100", "type": "Index", "exchange": "Istanbul"},
        "^XU100": {"query": "XU100", "type": "Index", "exchange": "Istanbul"},
        "TRY=X": {"query": "USD/TRY", "type": "FX", "exchange": ""},
        "USDTRY=X": {"query": "USD/TRY", "type": "FX", "exchange": ""},
        "XAUTRY=X": {"query": "XAU/TRY", "type": "FX", "exchange": ""},
        "XAUUSD=X": {"query": "XAU/USD", "type": "FX", "exchange": ""},
        "GC=F": {"query": "Gold", "type": "Commodity", "exchange": ""},
    }

    def __init__(self, owner) -> None:
        self._owner = owner
        self._investing_id_cache: Dict[tuple[str, str, str], Optional[int]] = {}
        self._series_cache: Dict[tuple[str, date, date], Dict[date, Decimal]] = {}

    def fetch_series_for_ticker(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> Dict[date, Decimal]:
        alias = self._get_investing_alias(ticker)
        if alias is None:
            return {}

        cache_key = (ticker.upper(), start_date, end_date)
        if cache_key in self._series_cache:
            return dict(self._series_cache[cache_key])

        investing_id = self._resolve_investing_symbol_id(alias)
        if investing_id is None:
            self._series_cache[cache_key] = {}
            return {}

        from_timestamp = int(pd.Timestamp(start_date, tz="UTC").timestamp())
        to_timestamp = int(pd.Timestamp(end_date + timedelta(days=1), tz="UTC").timestamp())

        try:
            data = self._owner._request_to_investing(
                "history",
                {
                    "symbol": investing_id,
                    "from": from_timestamp,
                    "to": to_timestamp,
                    "resolution": "D",
                },
            )
        except Exception:
            logger.debug("Investing gecmis verisi alinamadi: %s", ticker, exc_info=True)
            self._series_cache[cache_key] = {}
            return {}

        if data.get("s") != "ok":
            self._series_cache[cache_key] = {}
            return {}

        timestamps = data.get("t") or []
        closes = data.get("c") or []
        result: Dict[date, Decimal] = {}
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            point_date = pd.Timestamp(ts, unit="s", tz="UTC").date()
            if start_date <= point_date <= end_date:
                result[point_date] = Decimal(str(float(close)))

        self._series_cache[cache_key] = dict(result)
        return result

    def _get_investing_alias(self, ticker: str) -> Optional[dict]:
        return self.INVESTING_SEARCH_ALIASES.get((ticker or "").upper())

    def _resolve_investing_symbol_id(self, alias: dict) -> Optional[int]:
        cache_key = (
            str(alias.get("query", "")),
            str(alias.get("type", "")),
            str(alias.get("exchange", "")),
        )
        if cache_key in self._investing_id_cache:
            return self._investing_id_cache[cache_key]

        results = self._owner._request_to_investing(
            "search",
            {
                "query": cache_key[0],
                "limit": 10,
                "type": cache_key[1],
                "exchange": cache_key[2],
            },
        )
        investing_id: Optional[int] = None
        for candidate in results or []:
            candidate_type = str(candidate.get("type", "") or candidate.get("pair_type", ""))
            candidate_exchange = str(candidate.get("exchange", "") or "")
            if cache_key[1] and candidate_type.lower() != cache_key[1].lower():
                continue
            if cache_key[2] and candidate_exchange.lower() != cache_key[2].lower():
                continue
            investing_id = self._extract_investing_id(candidate)
            if investing_id is not None:
                break

        if investing_id is None:
            for candidate in results or []:
                investing_id = self._extract_investing_id(candidate)
                if investing_id is not None:
                    break

        self._investing_id_cache[cache_key] = investing_id
        return investing_id

    def _extract_investing_id(self, candidate: dict) -> Optional[int]:
        for field in ("ticker", "pair_ID", "pairId", "id"):
            raw_value = candidate.get(field)
            if raw_value is None:
                continue
            try:
                return int(raw_value)
            except (TypeError, ValueError):
                continue
        return None


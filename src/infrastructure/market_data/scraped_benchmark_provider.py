from __future__ import annotations

import logging
import re
from datetime import date
from decimal import Decimal
from typing import Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ScrapedBenchmarkProvider:
    COUNTRY_ECONOMY_BIST_MONTH_URL = "https://countryeconomy.com/stock-exchange/turkey?dr={month_key}"
    EXCHANGE_RATES_USDTRY_YEAR_URL = "https://www.exchange-rates.org/exchange-rate-history/usd-try-{year}"
    MACROTRENDS_GOLD_DAILY_URL = "https://www.macrotrends.net/economic-data/2627/D"
    COUNTRY_ECONOMY_BIST_ROW_PATTERN = re.compile(
        r"<tr[^>]*>\s*<td[^>]*>\s*(\d{2}/\d{2}/\d{4})\s*</td>\s*<td[^>]*>\s*([\d,.]+)\s*</td>",
        re.IGNORECASE | re.DOTALL,
    )
    EXCHANGE_RATES_USDTRY_ROW_PATTERN = re.compile(
        r'<a href="/exchange-rate-history/usd-try-\d{4}-\d{2}-\d{2}" class="w">([^<]+)</a>\s*'
        r'<a href="/exchange-rate-history/usd-try-\d{4}-\d{2}-\d{2}" class="n">[^<]+</a>\s*</td>\s*<td>\s*'
        r'<span class="w"><span class="nowrap">1 USD =</span>\s*<span class="nowrap">([\d.]+)\s+TRY</span>',
        re.IGNORECASE | re.DOTALL,
    )

    def __init__(self, owner) -> None:
        self._owner = owner
        self._countryeconomy_month_cache: Dict[str, Dict[date, Decimal]] = {}
        self._exchange_rates_year_cache: Dict[int, Dict[date, Decimal]] = {}
        self._macrotrends_gold_daily_cache: Optional[Dict[date, Decimal]] = None

    def fetch_series_for_ticker(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> Optional[Dict[date, Decimal]]:
        normalized_ticker = (ticker or "").upper()
        if normalized_ticker in {"XU100.IS", "^XU100"}:
            return self._fetch_countryeconomy_bist_series(start_date, end_date)
        if normalized_ticker in {"TRY=X", "USDTRY=X"}:
            return self._fetch_exchange_rates_usdtry_series(start_date, end_date)
        if normalized_ticker in {"XAUUSD=X", "GC=F"}:
            return self._fetch_macrotrends_gold_series(start_date, end_date)
        if normalized_ticker == "XAUTRY=X":
            gold_series = self._fetch_macrotrends_gold_series(start_date, end_date)
            usd_try_series = self._fetch_exchange_rates_usdtry_series(start_date, end_date)
            return self._combine_series(gold_series, usd_try_series)
        return None

    def _filter_series_for_range(
        self,
        series: Dict[date, Decimal],
        start_date: date,
        end_date: date,
    ) -> Dict[date, Decimal]:
        return {
            point_date: value
            for point_date, value in series.items()
            if start_date <= point_date <= end_date
        }

    def _next_month_start(self, month_start: date) -> date:
        if month_start.month == 12:
            return date(month_start.year + 1, 1, 1)
        return date(month_start.year, month_start.month + 1, 1)

    def _month_starts_between(self, start_date: date, end_date: date) -> list[date]:
        current = date(start_date.year, start_date.month, 1)
        last = date(end_date.year, end_date.month, 1)
        months: list[date] = []
        while current <= last:
            months.append(current)
            current = self._next_month_start(current)
        return months

    def _fetch_countryeconomy_bist_month(self, month_key: str) -> Dict[date, Decimal]:
        if month_key in self._countryeconomy_month_cache:
            return dict(self._countryeconomy_month_cache[month_key])

        url = self.COUNTRY_ECONOMY_BIST_MONTH_URL.format(month_key=month_key)
        try:
            html = self._owner._request_text(url)
        except Exception:
            logger.debug("Countryeconomy BIST 100 verisi alinamadi: %s", month_key, exc_info=True)
            self._countryeconomy_month_cache[month_key] = {}
            return {}

        result: Dict[date, Decimal] = {}
        for raw_date, raw_value in self.COUNTRY_ECONOMY_BIST_ROW_PATTERN.findall(html):
            try:
                point_date = pd.to_datetime(raw_date, format="%m/%d/%Y").date()
                result[point_date] = Decimal(raw_value.replace(",", ""))
            except (TypeError, ValueError):
                continue

        self._countryeconomy_month_cache[month_key] = dict(result)
        return result

    def _fetch_countryeconomy_bist_series(
        self,
        start_date: date,
        end_date: date,
    ) -> Dict[date, Decimal]:
        result: Dict[date, Decimal] = {}
        for month_start in self._month_starts_between(start_date, end_date):
            month_key = month_start.strftime("%Y-%m")
            result.update(self._fetch_countryeconomy_bist_month(month_key))
        return self._filter_series_for_range(result, start_date, end_date)

    def _fetch_exchange_rates_usdtry_year(self, year: int) -> Dict[date, Decimal]:
        if year in self._exchange_rates_year_cache:
            return dict(self._exchange_rates_year_cache[year])

        url = self.EXCHANGE_RATES_USDTRY_YEAR_URL.format(year=year)
        try:
            html = self._owner._request_text(url)
        except Exception:
            logger.debug("Exchange-rates USD/TRY verisi alinamadi: %s", year, exc_info=True)
            self._exchange_rates_year_cache[year] = {}
            return {}

        result: Dict[date, Decimal] = {}
        for raw_date, raw_value in self.EXCHANGE_RATES_USDTRY_ROW_PATTERN.findall(html):
            try:
                point_date = pd.to_datetime(raw_date, format="%B %d, %Y").date()
                result[point_date] = Decimal(raw_value)
            except (TypeError, ValueError):
                continue

        self._exchange_rates_year_cache[year] = dict(result)
        return result

    def _fetch_exchange_rates_usdtry_series(
        self,
        start_date: date,
        end_date: date,
    ) -> Dict[date, Decimal]:
        result: Dict[date, Decimal] = {}
        for year in range(start_date.year, end_date.year + 1):
            result.update(self._fetch_exchange_rates_usdtry_year(year))
        return self._filter_series_for_range(result, start_date, end_date)

    def _fetch_macrotrends_gold_daily_series(self) -> Dict[date, Decimal]:
        if self._macrotrends_gold_daily_cache is not None:
            return dict(self._macrotrends_gold_daily_cache)

        try:
            payload = self._owner._request_json(self.MACROTRENDS_GOLD_DAILY_URL)
        except Exception:
            logger.debug("Macrotrends altin verisi alinamadi", exc_info=True)
            self._macrotrends_gold_daily_cache = {}
            return {}

        result: Dict[date, Decimal] = {}
        for point in payload.get("data") or []:
            if not isinstance(point, (list, tuple)) or len(point) < 2 or point[1] is None:
                continue
            try:
                point_date = pd.Timestamp(int(point[0]), unit="ms", tz="UTC").date()
                result[point_date] = Decimal(str(float(point[1])))
            except (TypeError, ValueError):
                continue

        self._macrotrends_gold_daily_cache = dict(result)
        return result

    def _fetch_macrotrends_gold_series(
        self,
        start_date: date,
        end_date: date,
    ) -> Dict[date, Decimal]:
        return self._filter_series_for_range(self._fetch_macrotrends_gold_daily_series(), start_date, end_date)

    def _combine_series(
        self,
        left_series: Dict[date, Decimal],
        right_series: Dict[date, Decimal],
    ) -> Dict[date, Decimal]:
        shared_dates = sorted(set(left_series).intersection(right_series))
        return {
            point_date: left_series[point_date] * right_series[point_date]
            for point_date in shared_dates
        }


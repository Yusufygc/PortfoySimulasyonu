# src/infrastructure/market_data/yfinance_client.py

from __future__ import annotations

import json
import logging
import re
import tempfile
import warnings
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, Optional, Sequence
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

import yfinance as yf
import pandas as pd
from pandas.errors import Pandas4Warning

from src.domain.ports.services.i_market_data_client import IMarketDataClient

logger = logging.getLogger(__name__)


class YFinanceMarketDataClient(IMarketDataClient):
    """
    IMarketDataClient arayüzünü yfinance ile implemente eden sınıf.

    Notlar:
      - yfinance.download() fonksiyonunda `end` tarihi EXCLUSIVE (hariç).
        Yani 2024-01-01 için veri istiyorsak: start=2024-01-01, end=2024-01-02.
      - BIST hisseleri için tipik ticker formatı: 'AKBNK.IS', 'ASELS.IS' vb.
    """

    INVESTING_SEARCH_ALIASES = {
        "XU100.IS": {"query": "XU100", "type": "Index", "exchange": "Istanbul"},
        "^XU100": {"query": "XU100", "type": "Index", "exchange": "Istanbul"},
        "TRY=X": {"query": "USD/TRY", "type": "FX", "exchange": ""},
        "USDTRY=X": {"query": "USD/TRY", "type": "FX", "exchange": ""},
        "XAUTRY=X": {"query": "XAU/TRY", "type": "FX", "exchange": ""},
        "XAUUSD=X": {"query": "XAU/USD", "type": "FX", "exchange": ""},
        "GC=F": {"query": "Gold", "type": "Commodity", "exchange": ""},
    }
    SCRAPED_BENCHMARK_TICKERS = frozenset({"XU100.IS", "^XU100", "TRY=X", "USDTRY=X", "XAUTRY=X", "XAUUSD=X", "GC=F"})
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

    def __init__(self, timeout: int = 10) -> None:
        self._timeout = timeout
        self._investing_id_cache: Dict[tuple[str, str, str], Optional[int]] = {}
        self._series_cache: Dict[tuple[str, date, date], Dict[date, Decimal]] = {}
        self._countryeconomy_month_cache: Dict[str, Dict[date, Decimal]] = {}
        self._exchange_rates_year_cache: Dict[int, Dict[date, Decimal]] = {}
        self._macrotrends_gold_daily_cache: Optional[Dict[date, Decimal]] = None
        cache_dir = Path(tempfile.gettempdir()) / "portfoy-simulasyonu" / "yfinance-cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        yf.set_tz_cache_location(str(cache_dir))
        warnings.filterwarnings(
            "ignore",
            message="Timestamp.utcnow is deprecated and will be removed in a future version.*",
            category=Pandas4Warning,
            module=r"yfinance\..*",
        )

    # ----------------- Yardımcı metotlar ----------------- #

    def _next_date(self, d: date) -> date:
        """Verilen tarihten bir gün sonrasını döner."""
        return d + timedelta(days=1)

    def _to_decimal(self, value) -> Decimal:
        """
        yfinance/pandas'dan gelen float/np.float tiplerini güvenli şekilde Decimal'e çevir.
        """
        return Decimal(str(float(value.squeeze())))

    def _download_dataframe(self, tickers, start: date, end: date):
        return yf.download(
            tickers=tickers,
            start=start,
            end=end,
            interval="1d",
            progress=False,
            auto_adjust=False,
            timeout=self._timeout,
        )

    def _request_text(self, url: str) -> str:
        request = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        with urlopen(request, timeout=self._timeout) as response:
            return response.read().decode("utf-8", errors="ignore")

    def _request_json(self, url: str):
        return json.loads(self._request_text(url))

    def _is_scraped_benchmark_ticker(self, ticker: str) -> bool:
        return (ticker or "").upper() in self.SCRAPED_BENCHMARK_TICKERS

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
            html = self._request_text(url)
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
            html = self._request_text(url)
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
            payload = self._request_json(self.MACROTRENDS_GOLD_DAILY_URL)
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

    def _fetch_scraped_series_for_ticker(
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

    def _get_investing_alias(self, ticker: str) -> Optional[dict]:
        return self.INVESTING_SEARCH_ALIASES.get((ticker or "").upper())

    def _request_to_investing(self, endpoint: str, params: Dict[str, object]):
        query = urlencode(params)
        url = f"https://tvc6.investing.com/{uuid4().hex}/0/0/0/0/{endpoint}?{query}"
        request = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/104.0.5112.102 Safari/537.36"
                ),
                "Referer": "https://tvc-invdn-com.investing.com/",
                "Content-Type": "application/json",
            },
        )
        with urlopen(request, timeout=self._timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload

    def _resolve_investing_symbol_id(self, alias: dict) -> Optional[int]:
        cache_key = (
            str(alias.get("query", "")),
            str(alias.get("type", "")),
            str(alias.get("exchange", "")),
        )
        if cache_key in self._investing_id_cache:
            return self._investing_id_cache[cache_key]

        results = self._request_to_investing(
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

    def _fetch_investing_series_for_ticker(
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
            data = self._request_to_investing(
                "history",
                {
                    "symbol": investing_id,
                    "from": from_timestamp,
                    "to": to_timestamp,
                    "resolution": "D",
                },
            )
        except Exception:
            logger.debug("Investing geçmiş verisi alınamadı: %s", ticker, exc_info=True)
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


    # ----------------- Tekil kapanış fiyatı ----------------- #

    def get_closing_price(self, stock_id: int, ticker: str, price_date: date) -> Decimal:
        """
        Tek bir hisse için belirli bir tarihteki kapanış fiyatını döner.

        Eğer ilgili günde veri yoksa (tatil, hafta sonu vb.):
          - ValueError fırlatır.
          - İstersen burada en yakın önceki günü arayacak bir mantık da ekleyebiliriz
            ama şimdilik domain/service katmanına bırakıyoruz.
        """
        start = price_date
        end = self._next_date(price_date)

        scraped_series = self._fetch_scraped_series_for_ticker(ticker, price_date, price_date)
        if scraped_series is not None:
            if price_date in scraped_series:
                return scraped_series[price_date]
            raise ValueError(f"{ticker} için {price_date} gün sonu fiyatı bulunamadı.")

        investing_series = self._fetch_investing_series_for_ticker(ticker, price_date, price_date)
        if investing_series:
            return investing_series[price_date]

        df = self._download_dataframe(ticker, start, end)

        if df.empty:
            raise ValueError(f"{ticker} için {price_date} gün sonu fiyatı bulunamadı.")

        # Günlük veride tek satır var; Close sütunundan alıyoruz.
        close_val = df["Close"].iloc[-1]
        return self._to_decimal(close_val)

    # ----------------- Toplu kapanış fiyatı ----------------- #

    def get_closing_prices(
        self,
        stock_ids: Sequence[int],
        tickers: Sequence[str],
        price_date: date,
    ) -> Dict[int, Decimal]:
        """
        Birden fazla hisse için toplu kapanış fiyatı.

        Parametreler:
          stock_ids: [1, 3, 7, ...]
          tickers:   ['AKBNK.IS', 'ASELS.IS', ...]  # aynı index ile eşleşecek

        Dönüş:
          { stock_id: close_price }

        Not:
          - yfinance, birden fazla ticker verince kolon yapısı MultiIndex olabiliyor.
          - Veri gelmeyen hisseler map'e eklenmez (loglama istersen ileride logger ekleriz).
        """
        if len(stock_ids) != len(tickers):
            raise ValueError("stock_ids ve tickers uzunluğu aynı olmalıdır.")

        if not stock_ids:
            return {}

        investing_results: Dict[int, Decimal] = {}
        remaining_pairs = []
        for stock_id, ticker in zip(stock_ids, tickers):
            scraped_series = self._fetch_scraped_series_for_ticker(ticker, price_date, price_date)
            if scraped_series is not None:
                if price_date in scraped_series:
                    investing_results[stock_id] = scraped_series[price_date]
                continue
            investing_series = self._fetch_investing_series_for_ticker(ticker, price_date, price_date)
            if investing_series:
                investing_results[stock_id] = investing_series[price_date]
            else:
                remaining_pairs.append((stock_id, ticker))

        if not remaining_pairs:
            return investing_results

        start = price_date
        end = self._next_date(price_date)
        remaining_ids = [stock_id for stock_id, _ in remaining_pairs]
        remaining_tickers = [ticker for _, ticker in remaining_pairs]

        # yfinance: birden çok ticker'ı liste olarak da alıyor
        df = self._download_dataframe(list(remaining_tickers), start, end)

        if df.empty:
            # Hiçbir veri yoksa direkt boş döneriz (service katmanı handle eder)
            return investing_results

        result: Dict[int, Decimal] = dict(investing_results)

        # İki durum var:
        # 1) Tek ticker: df.columns normal Index -> Close sütunu var
        # 2) Çoklu ticker: df.columns MultiIndex -> ('Close', 'AKBNK.IS') gibi

        if isinstance(df.columns, pd.MultiIndex):
            # Çoklu ticker
            # df: index = DatetimeIndex, columns = MultiIndex(levels: ['Adj Close','Close',...], tickers)
            # İlgili tek gün için satır: df.iloc[0]
            row = df.iloc[-1]

            for stock_id, ticker in zip(remaining_ids, remaining_tickers):
                try:
                    close_val = row["Close", ticker]
                except KeyError:
                    # Bu ticker için veri yok, atlıyoruz
                    continue
                if pd.isna(close_val):
                    continue
                result[stock_id] = self._to_decimal(close_val)
        else:
            # Tek ticker
            row = df.iloc[-1]
            close_val = row["Close"]
            if not pd.isna(close_val):
                # stock_ids, tickers tek elemanlı olmalı
                stock_id = remaining_ids[0]
                result[stock_id] = self._to_decimal(close_val)

        return result

    # ----------------- Tarih aralığı fiyat serisi ----------------- #

    def get_price_series(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> Dict[date, Decimal]:
        """
        Bir hissenin belirli bir tarih aralığındaki kapanış fiyat serisini döner.

        start_date dahil, end_date dahil olacak şekilde düşünüyoruz.
        yfinance 'end' tarihini EXCLUSIVE aldığı için end_date + 1 gönderiyoruz.

        Dönüş:
          {
            date1: Decimal(price1),
            date2: Decimal(price2),
            ...
          }
        """
        if start_date > end_date:
            raise ValueError("start_date end_date'ten büyük olamaz.")

        scraped_series = self._fetch_scraped_series_for_ticker(ticker, start_date, end_date)
        if scraped_series is not None:
            return scraped_series

        investing_series = self._fetch_investing_series_for_ticker(ticker, start_date, end_date)
        if investing_series:
            return investing_series

        yf_start = start_date
        yf_end = self._next_date(end_date)  # end exclusive

        df = self._download_dataframe(ticker, yf_start, yf_end)

        if df.empty:
            return {}

        # df.index: DatetimeIndex, df["Close"]: Series
        close_series = df["Close"]

        result: Dict[date, Decimal] = {}
        for ts, value in close_series.items():
            if pd.isna(value):
                continue
            d = ts.date()
            # Güvenlik: emin olalım aralık içinde
            if start_date <= d <= end_date:
                result[d] = self._to_decimal(value)

        return result

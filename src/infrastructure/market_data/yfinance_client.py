from __future__ import annotations

import json
import logging
import tempfile
import warnings
from datetime import date
from pathlib import Path
from typing import Dict, Sequence
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

import yfinance as yf
from pandas.errors import Pandas4Warning

from src.domain.ports.services.i_market_data_client import IMarketDataClient

from .investing_fallback_client import InvestingFallbackClient
from .scraped_benchmark_provider import ScrapedBenchmarkProvider
from .yfinance_price_client import YFinancePriceClient

logger = logging.getLogger(__name__)


class YFinanceMarketDataClient(IMarketDataClient):
    """
    Thin facade over dedicated market-data providers.
    """

    def __init__(self, timeout: int = 10) -> None:
        self._timeout = timeout
        cache_dir = Path(tempfile.gettempdir()) / "portfoy-simulasyonu" / "yfinance-cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        yf.set_tz_cache_location(str(cache_dir))
        warnings.filterwarnings(
            "ignore",
            message="Timestamp.utcnow is deprecated and will be removed in a future version.*",
            category=Pandas4Warning,
            module=r"yfinance\..*",
        )
        self._scraped_provider = ScrapedBenchmarkProvider(self)
        self._investing_client = InvestingFallbackClient(self)
        self._price_client = YFinancePriceClient(self)

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
            return json.loads(response.read().decode("utf-8"))

    def get_closing_price(self, stock_id: int, ticker: str, price_date: date):
        return self._price_client.get_closing_price(ticker=ticker, price_date=price_date)

    def get_closing_prices(
        self,
        stock_ids: Sequence[int],
        tickers: Sequence[str],
        price_date: date,
    ):
        return self._price_client.get_closing_prices(stock_ids=stock_ids, tickers=tickers, price_date=price_date)

    def get_price_series(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ):
        return self._price_client.get_price_series(ticker=ticker, start_date=start_date, end_date=end_date)

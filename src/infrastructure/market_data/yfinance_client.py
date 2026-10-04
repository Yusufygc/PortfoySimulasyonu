from __future__ import annotations

import logging
import tempfile
import warnings
from datetime import date
from pathlib import Path

import yfinance as yf
try:
    from pandas.errors import Pandas4Warning
except ImportError:
    class Pandas4Warning(Warning):
        pass

from src.domain.exceptions import MarketDataUnavailableError
from src.domain.ticker import to_yf_symbol
from src.infrastructure.retry import retry_call
from ._errors import MARKET_DATA_FALLBACK_ERRORS
from .yfinance_price_client import YFinancePriceClient

logger = logging.getLogger(__name__)


from src.domain.ports.services.i_market_data_client import IMarketDataClient

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
        self._price_client = YFinancePriceClient(self)

    def _download_dataframe(self, tickers, start: date, end: date):
        from .yfinance_lock import yfinance_lock

        def download():
            # Kilit denemeler arasında bırakılır; bekleme sırasında diğer yfinance çağrıları engellenmez.
            with yfinance_lock:
                return yf.download(
                    tickers=tickers,
                    start=start,
                    end=end,
                    interval="1d",
                    progress=False,
                    auto_adjust=True,
                    timeout=self._timeout,
                )

        try:
            return retry_call(download, label="YFinance indirme")
        except MARKET_DATA_FALLBACK_ERRORS as e:
            raise MarketDataUnavailableError(f"YFinance indirme hatasi: {e}") from e

    # Kanonik ticker uzantısızdır (`THYAO`); yfinance borsa son eki (`THYAO.IS`) ister, bu yüzden sınırda çevrilir.
    def get_closing_price(self, stock_id: int, ticker: str, price_date: date):
        return self._price_client.get_closing_price(ticker=to_yf_symbol(ticker), price_date=price_date)

    def get_price_series(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ):
        return self._price_client.get_price_series(
            ticker=to_yf_symbol(ticker), start_date=start_date, end_date=end_date
        )

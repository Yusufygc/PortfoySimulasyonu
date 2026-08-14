"""
TradingView veri istemcisi — tradingview-datafeed kütüphanesi üzerinden.

Kullanım amacı: EMA hesabının TradingView ile birebir uyuşması için
fiyat verilerini yfinance yerine doğrudan TV'den çekmek.

Kısıtlar:
- Anonim bağlantı rate-limit'e tabidir; TV hesabı opsiyoneldir.
- Yalnızca günlük (daily) verisi desteklenir (EMA cross için yeterli).
- Global hisseler için exchange bilgisi gerekir; BIST otomatik tespit edilir.
"""
from __future__ import annotations

import logging
import re
import time
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Optional, Sequence

import pandas as pd

from src.domain.ports.services.i_market_data_client import IMarketDataClient

logger = logging.getLogger(__name__)

# suffix → exchange
_SUFFIX_EXCHANGE: dict[str, str] = {
    ".IS": "BIST",
    ".PA": "EURONEXT",
    ".L":  "LSE",
    ".DE": "XETRA",
    ".F":  "XETRA",
    ".MI": "MIL",
    ".AS": "EURONEXT",
    ".BR": "EURONEXT",
}

# Geçerli ticker formatı: 1-10 harf/rakam, opsiyonel exchange suffix
_VALID_TICKER_RE = re.compile(r"^[A-Z0-9]{1,10}(\.[A-Z]{1,4})?$")

# Timeout sonrası kaç kez bağlantıyı yenile
_MAX_RETRIES = 2
# Hata sonrası bekleme (saniye) — rate limit için
_RETRY_DELAY = 2.0


def _parse_ticker(ticker: str) -> tuple[str, str]:
    """'THYAO.IS' → ('THYAO', 'BIST').  Suffix yok → NASDAQ."""
    upper = ticker.upper()
    for suffix, exchange in _SUFFIX_EXCHANGE.items():
        if upper.endswith(suffix):
            return upper[: -len(suffix)], exchange
    return upper, "NASDAQ"


def _is_valid_ticker(ticker: str) -> bool:
    """Açıkça geçersiz ticker'ları filtrele (BIST sembolü max 10 harf, alfanumerik)."""
    return bool(_VALID_TICKER_RE.match(ticker.upper()))


def _n_bars(start_date: date, end_date: date) -> int:
    """Tahmini işlem günü sayısı + %30 buffer."""
    calendar_days = max((end_date - start_date).days, 1)
    return int(calendar_days * 260 / 365 * 1.3) + 100


class TvDatafeedClient(IMarketDataClient):
    """
    IMarketDataClient implementasyonu — TradingView (tradingview-datafeed).

    Args:
        username: TV kullanıcı adı (opsiyonel, anonim çalışır)
        password: TV şifresi (opsiyonel)
    """

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self._username = username
        self._password = password
        self._tv = None  # lazy init

    # ------------------------------------------------------------------
    # IMarketDataClient
    # ------------------------------------------------------------------

    def get_closing_price(self, stock_id: int, ticker: str, price_date: date) -> Decimal:
        series = self.get_price_series(ticker, price_date - timedelta(days=7), price_date)
        if not series:
            raise ValueError(f"TV: {ticker} için {price_date} fiyatı bulunamadı.")
        return series[max(series)]

    def get_closing_prices(
        self,
        stock_ids: Sequence[int],
        tickers: Sequence[str],
        price_date: date,
    ) -> Dict[int, Decimal]:
        result: Dict[int, Decimal] = {}
        for sid, ticker in zip(stock_ids, tickers):
            try:
                result[sid] = self.get_closing_price(sid, ticker, price_date)
            except Exception:
                logger.warning("TV: %s fiyatı alınamadı, atlandı", ticker)
        return result

    def get_price_series(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> Dict[date, Decimal]:
        try:
            from tvDatafeed import Interval
        except ImportError:
            raise RuntimeError(
                "tradingview-datafeed kurulu değil. "
                "Kurmak için: pip install tradingview-datafeed"
            )

        if not _is_valid_ticker(ticker):
            logger.debug("TV: %s geçersiz ticker formatı, atlanıyor.", ticker)
            return {}

        symbol, exchange = _parse_ticker(ticker)
        n_bars = _n_bars(start_date, end_date)

        df = self._fetch_with_retry(symbol, exchange, Interval.in_daily, n_bars)
        if df is None or df.empty:
            return {}

        result: Dict[date, Decimal] = {}
        close_col = "close" if "close" in df.columns else "Close"
        for ts, row in df.iterrows():
            d: date = ts.date() if hasattr(ts, "date") else ts
            if start_date <= d <= end_date:
                raw = row.get(close_col)
                if raw is not None and not pd.isna(raw):
                    result[d] = Decimal(str(float(raw)))

        logger.debug("TV: %s → %d bar (%s … %s)", ticker, len(result), start_date, end_date)
        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fetch_with_retry(self, symbol: str, exchange: str, interval, n_bars: int):
        """Timeout sonrası bağlantıyı yenileyerek tekrar dene."""
        for attempt in range(_MAX_RETRIES + 1):
            try:
                tv = self._get_tv()
                return tv.get_hist(
                    symbol=symbol,
                    exchange=exchange,
                    interval=interval,
                    n_bars=n_bars,
                )
            except Exception as exc:
                err_str = str(exc).lower()
                is_timeout = "timeout" in err_str or "timed out" in err_str
                if is_timeout and attempt < _MAX_RETRIES:
                    logger.debug(
                        "TV: %s/%s timeout (deneme %d/%d), bağlantı yenileniyor...",
                        symbol, exchange, attempt + 1, _MAX_RETRIES,
                    )
                    self._tv = None  # bağlantıyı sıfırla
                    time.sleep(_RETRY_DELAY)
                    continue
                logger.debug("TV: %s/%s veri yok (%s)", symbol, exchange, exc)
                return None
        return None

    def _get_tv(self):
        if self._tv is None:
            from tvDatafeed import TvDatafeed
            self._tv = TvDatafeed(self._username, self._password)
        return self._tv

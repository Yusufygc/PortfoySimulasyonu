from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd
import yfinance as yf

from src.domain.exceptions import MarketDataUnavailableError
from src.domain.models.asset_price import AssetQuote
from src.domain.ports.services.i_asset_price_provider import IAssetPriceProvider
from src.domain.ports.services.i_asset_symbol_verifier import IAssetSymbolVerifier
from src.infrastructure.market_data._errors import MARKET_DATA_FALLBACK_ERRORS
from src.infrastructure.retry import retry_call

logger = logging.getLogger(__name__)

BULK_CHUNK_SIZE = 50
INTRADAY_SIGNIFICANT_DIGITS = 7   # dakika barları float32 kalıntısı taşır (0.98 -> 0.9800000190734863)
DAILY_SIGNIFICANT_DIGITS = 7     # Yahoo günlük kapanışları da float32 kalıntısı taşır (3898.9 -> 3898.89990234)


def _symbol_frame(data: Any, symbol: str, symbol_count: int) -> Any:
    """Çok düzeyli sütunlarda sembolün alt tablosu; tek sembollü düz tabloda tablonun kendisi; yoksa None."""
    if isinstance(data.columns, pd.MultiIndex):
        return data[symbol] if symbol in data.columns.get_level_values(0) else None
    return data if symbol_count == 1 else None


def _to_decimal(value: float, significant_digits: int) -> Decimal:
    return Decimal(f"{float(value):.{significant_digits}g}")


def _naive_utc(stamp: Any) -> datetime:
    moment = pd.Timestamp(stamp)
    moment = moment.tz_localize("UTC") if moment.tzinfo is None else moment.tz_convert("UTC")
    return moment.to_pydatetime().astimezone(timezone.utc).replace(tzinfo=None)


def latest_quotes_from_download(data: Any, symbols: Sequence[str], significant_digits: int) -> Dict[str, AssetQuote]:
    """`yf.download(..., group_by="ticker")` çıktısından her sembolün son geçerli kapanışı."""
    if data is None or getattr(data, "empty", True):
        return {}
    result: Dict[str, AssetQuote] = {}
    for symbol in symbols:
        frame = _symbol_frame(data, symbol, len(symbols))
        if frame is None or "Close" not in frame:
            continue
        closes = frame["Close"].dropna()
        closes = closes[closes > 0]
        if closes.empty:
            continue
        result[symbol] = AssetQuote(
            symbol=symbol,
            price=_to_decimal(closes.iloc[-1], significant_digits),
            as_of=_naive_utc(closes.index[-1]),
        )
    return result


def daily_closes_from_download(data: Any, symbol: str) -> List[Tuple[date, Decimal]]:
    """Tek sembollü `yf.download` çıktısından (tarih, kapanış) listesi."""
    if data is None or getattr(data, "empty", True) or "Close" not in data:
        return []
    close_col = data["Close"]
    if isinstance(close_col, pd.DataFrame):
        close_col = close_col[symbol] if symbol in close_col.columns else close_col.iloc[:, 0]
    points: List[Tuple[date, Decimal]] = []
    for stamp, value in close_col.items():
        if pd.isna(value) or float(value) <= 0:
            continue
        points.append((pd.Timestamp(stamp).date(), _to_decimal(value, DAILY_SIGNIFICANT_DIGITS)))
    return sorted(points)


class YFinanceAssetPriceProvider(IAssetPriceProvider, IAssetSymbolVerifier):
    """yfinance tabanlı fiyat sağlayıcı: ABD hissesi, kripto, emtia vadeli kontratı ve kur sembolleri."""

    def __init__(self, timeout: int = 10) -> None:
        self._timeout = timeout

    def get_latest(self, symbols: Sequence[str]) -> Dict[str, AssetQuote]:
        unique = list(dict.fromkeys(symbol for symbol in symbols if symbol))
        result: Dict[str, AssetQuote] = {}
        for start in range(0, len(unique), BULK_CHUNK_SIZE):
            chunk = unique[start:start + BULK_CHUNK_SIZE]
            result.update(self._download_latest(chunk, "1d", "1m", INTRADAY_SIGNIFICANT_DIGITS))
            missing = [symbol for symbol in chunk if symbol not in result]
            if missing:  # piyasa kapalı: dakika barı yok, son günlük kapanışa düşülür
                result.update(self._download_latest(missing, "5d", "1d", DAILY_SIGNIFICANT_DIGITS))
        return result

    def _download_latest(self, symbols: List[str], period: str, interval: str, digits: int) -> Dict[str, AssetQuote]:
        from .yfinance_lock import yfinance_lock

        def download():
            with yfinance_lock:
                return yf.download(
                    " ".join(symbols), period=period, interval=interval, group_by="ticker",
                    auto_adjust=False, threads=True, progress=False, timeout=self._timeout,
                )

        try:
            data = retry_call(download, label="YFinance varlık fiyatı")
        except MARKET_DATA_FALLBACK_ERRORS as exc:
            logger.warning("Varlık fiyatı indirilemedi (%d sembol): %s", len(symbols), exc)
            return {}
        return latest_quotes_from_download(data, symbols, digits)

    def get_history(self, symbol: str, start: date, end: date) -> List[Tuple[date, Decimal]]:
        if start > end:
            raise ValueError("start end'den büyük olamaz.")
        from .yfinance_lock import yfinance_lock

        def download():
            with yfinance_lock:
                return yf.download(
                    symbol, start=start, end=end + timedelta(days=1), interval="1d",
                    auto_adjust=True, progress=False, timeout=self._timeout,
                )

        try:
            data = retry_call(download, label="YFinance varlık geçmişi")
        except MARKET_DATA_FALLBACK_ERRORS as exc:
            raise MarketDataUnavailableError(f"{symbol} geçmiş fiyatı alınamadı: {exc}") from exc
        return [point for point in daily_closes_from_download(data, symbol) if start <= point[0] <= end]

    def verify(self, yf_symbol: str) -> bool:
        """Son 5 günde en az bir geçerli kapanış varsa sembol geçerlidir. Ağ hatasında `MarketDataUnavailableError`."""
        from .yfinance_lock import yfinance_lock

        def download():
            with yfinance_lock:
                return yf.download(yf_symbol, period="5d", interval="1d", auto_adjust=True,
                                   progress=False, timeout=self._timeout)

        try:
            data = retry_call(download, label="YFinance sembol doğrulama")
        except MARKET_DATA_FALLBACK_ERRORS as exc:
            raise MarketDataUnavailableError(f"{yf_symbol} doğrulanamadı: {exc}") from exc
        return bool(daily_closes_from_download(data, yf_symbol))

"""yfinance ile artımlı günlük BIST barı indirme (`IMarketBarDownloader`); 50'lik toplu istekler."""
from __future__ import annotations

import logging
from datetime import date
from typing import List, Sequence, Tuple

import pandas as pd
import yfinance as yf

from src.domain.models.market_bar import MarketBar
from src.domain.ports.repositories.i_market_history_store import IMarketBarDownloader
from src.infrastructure.market_data.bar_quality import is_ghost_bar

logger = logging.getLogger(__name__)

CHUNK_SIZE = 50


def _bars_from_frame(ticker: str, frame: pd.DataFrame) -> List[MarketBar]:
    frame = frame.reset_index()
    date_col = "Date" if "Date" in frame.columns else frame.columns[0]
    bars: List[MarketBar] = []
    for record in frame.to_dict("records"):
        close = float(record.get("Close", 0) or 0)
        if not close > 0:  # geçerli kapanışı olmayan satırlar alınmaz
            continue
        volume = record.get("Volume")
        price_date = pd.to_datetime(record[date_col]).date()
        if is_ghost_bar(price_date, (record.get("Open"), record.get("High"), record.get("Low"), close, volume)):
            continue  # tatil günü veya hacimsiz sabit bar: işlem günü değil
        bars.append(MarketBar(
            ticker=ticker,
            price_date=price_date,
            close_price=close,
            open_price=float(record["Open"]),
            high_price=float(record["High"]),
            low_price=float(record["Low"]),
            volume=0 if volume is None or volume != volume else int(volume),
        ))
    return bars


class YFinanceBistBarDownloader(IMarketBarDownloader):
    def download_daily(
        self, tickers: Sequence[str], start: date, end_exclusive: date
    ) -> Tuple[List[MarketBar], int, List[str]]:
        bars: List[MarketBar] = []
        updated = 0
        errors: List[str] = []
        for i in range(0, len(tickers), CHUNK_SIZE):
            chunk = list(tickers[i : i + CHUNK_SIZE])
            try:
                data = yf.download(
                    " ".join(f"{tk}.IS" for tk in chunk), start=start.isoformat(), end=end_exclusive.isoformat(),
                    group_by="ticker", auto_adjust=False, threads=True, progress=False,
                )
            except Exception as batch_err:
                message = f"Batch indirme hatası (blok {i}): {batch_err}"
                logger.warning(message)
                errors.append(message)
                continue
            if data is None or data.empty:
                continue
            for ticker in chunk:
                frame = self._frame_for(data, ticker, len(chunk) == 1)
                if frame is None or frame.empty:
                    continue
                try:
                    found = _bars_from_frame(ticker, frame)
                except Exception as sub_err:
                    logger.debug("Hisse parse hatası (%s): %s", ticker, sub_err)
                    continue
                if found:
                    bars.extend(found)
                    updated += 1
        return bars, updated, errors

    @staticmethod
    def _frame_for(data: pd.DataFrame, ticker: str, single: bool):
        if single:
            return data.copy()
        symbol = f"{ticker}.IS"
        if symbol in data.columns.levels[0]:
            return data[symbol].dropna(how="all").copy()
        return None

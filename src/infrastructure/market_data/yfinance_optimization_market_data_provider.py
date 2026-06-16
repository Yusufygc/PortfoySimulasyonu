from __future__ import annotations

from typing import List, Optional

import pandas as pd
import yfinance as yf

from src.infrastructure.market_data._errors import MARKET_DATA_FALLBACK_ERRORS


class YFinanceOptimizationMarketDataProvider:
    def get_historical_prices(self, tickers: List[str], days: int) -> pd.DataFrame:
        from .yfinance_lock import yfinance_lock
        try:
            with yfinance_lock:
                df = yf.download(
                    tickers=tickers,
                    period=f"{days}d",
                    interval="1d",
                    progress=False,
                    auto_adjust=False,
                    timeout=15,
                )
        except MARKET_DATA_FALLBACK_ERRORS as exc:
            raise ValueError(f"Fiyat verisi cekilemedi: {exc}") from exc

        if df.empty:
            return pd.DataFrame()

        if isinstance(df.columns, pd.MultiIndex):
            close_df = df["Close"]
        else:
            close_df = df[["Close"]].rename(columns={"Close": tickers[0]})

        # En az 60 gunluk gecerli verisi olan kolonları (hisseleri) koru
        valid_cols = [col for col in close_df.columns if close_df[col].notna().sum() >= 60]
        if not valid_cols:
            return pd.DataFrame()

        return close_df[valid_cols].dropna()

    def get_last_price(self, ticker: str) -> Optional[float]:
        from .yfinance_lock import yfinance_lock
        with yfinance_lock:
            try:
                yt = yf.Ticker(ticker)
                info = getattr(yt, "fast_info", None) or yt.info
                if isinstance(info, dict):
                    for key in ("lastPrice", "last_price", "regularMarketPrice", "currentPrice"):
                        value = info.get(key)
                        if value is not None:
                            return float(value)

                hist = yt.history(period="5d", auto_adjust=False)
                if hist is not None and not hist.empty and "Close" in hist:
                    close_series = hist["Close"].dropna()
                    if not close_series.empty:
                        return float(close_series.iloc[-1])
            except MARKET_DATA_FALLBACK_ERRORS:
                return None
            return None

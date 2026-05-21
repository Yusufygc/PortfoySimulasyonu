from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol

import pandas as pd
import yfinance as yf


@dataclass(frozen=True)
class OptimizationPolicy:
    trading_days_per_year: int = 252
    risk_free_rate: float = 0.30
    max_single_weight: float = 0.40


class OptimizationMarketDataProvider(Protocol):
    def get_historical_prices(self, tickers: List[str], days: int) -> pd.DataFrame:
        ...

    def get_last_price(self, ticker: str) -> Optional[float]:
        ...


class YFinanceOptimizationMarketDataProvider:
    def get_historical_prices(self, tickers: List[str], days: int) -> pd.DataFrame:
        try:
            df = yf.download(
                tickers=tickers,
                period=f"{days}d",
                interval="1d",
                progress=False,
                auto_adjust=False,
                timeout=15,
            )
        except Exception as exc:
            raise ValueError(f"Fiyat verisi cekilemedi: {exc}") from exc

        if df.empty:
            return pd.DataFrame()

        if isinstance(df.columns, pd.MultiIndex):
            close_df = df["Close"]
        else:
            close_df = df[["Close"]].rename(columns={"Close": tickers[0]})

        return close_df.dropna()

    def get_last_price(self, ticker: str) -> Optional[float]:
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
        except Exception:
            return None
        return None

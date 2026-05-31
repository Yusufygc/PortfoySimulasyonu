from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Sequence

import pandas as pd


class YFinancePriceClient:
    def __init__(self, owner) -> None:
        self._owner = owner

    @staticmethod
    def to_decimal(value) -> Decimal:
        if hasattr(value, "squeeze"):
            value = value.squeeze()
        return Decimal(str(float(value)))

    @staticmethod
    def next_date(point_date: date) -> date:

        return point_date + timedelta(days=1)

    def get_closing_price(self, ticker: str, price_date: date) -> Decimal:
        dataframe = self._owner._download_dataframe(ticker, price_date, self.next_date(price_date))
        if dataframe.empty:
            raise ValueError(f"{ticker} icin {price_date} gun sonu fiyati bulunamadi.")
        close_col = dataframe["Close"]
        if isinstance(dataframe.columns, pd.MultiIndex):
            close_series = close_col[ticker] if ticker in close_col.columns else close_col.iloc[:, 0]
        else:
            close_series = close_col
        return self.to_decimal(close_series.iloc[-1])

    def get_closing_prices(
        self,
        stock_ids: Sequence[int],
        tickers: Sequence[str],
        price_date: date,
    ) -> Dict[int, Decimal]:
        if len(stock_ids) != len(tickers):
            raise ValueError("stock_ids ve tickers uzunlugu ayni olmalidir.")
        if not stock_ids:
            return {}

        preloaded_results: Dict[int, Decimal] = {}
        remaining_pairs = list(zip(stock_ids, tickers))

        if not remaining_pairs:
            return preloaded_results

        remaining_ids = [stock_id for stock_id, _ in remaining_pairs]
        remaining_tickers = [ticker for _, ticker in remaining_pairs]
        dataframe = self._owner._download_dataframe(list(remaining_tickers), price_date, self.next_date(price_date))
        if dataframe.empty:
            return preloaded_results

        result: Dict[int, Decimal] = dict(preloaded_results)
        if isinstance(dataframe.columns, pd.MultiIndex):
            row = dataframe.iloc[-1]
            for stock_id, ticker in zip(remaining_ids, remaining_tickers):
                try:
                    close_value = row["Close", ticker]
                except KeyError:
                    continue
                if pd.isna(close_value):
                    continue
                result[stock_id] = self.to_decimal(close_value)
        else:
            close_value = dataframe.iloc[-1]["Close"]
            if not pd.isna(close_value):
                result[remaining_ids[0]] = self.to_decimal(close_value)
        return result

    def get_price_series(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> Dict[date, Decimal]:
        if start_date > end_date:
            raise ValueError("start_date end_date'ten buyuk olamaz.")

        # En yakın geçmiş işlem gününü bulabilmek için 10 gün geriden taramaya başlıyoruz
        lookback_start = start_date - timedelta(days=10)
        dataframe = self._owner._download_dataframe(ticker, lookback_start, self.next_date(end_date))
        if dataframe.empty:
            return {}

        close_col = dataframe["Close"]
        if isinstance(dataframe.columns, pd.MultiIndex):
            close_series = close_col[ticker] if ticker in close_col.columns else close_col.iloc[:, 0]
        else:
            close_series = close_col

        result: Dict[date, Decimal] = {}
        for timestamp, value in close_series.items():
            if pd.isna(value):
                continue
            point_date = timestamp.date()
            if point_date <= end_date:
                result[point_date] = self.to_decimal(value)
        return result


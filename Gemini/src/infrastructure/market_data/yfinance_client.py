# src/infrastructure/market_data/yfinance_client.py

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Sequence

import yfinance as yf
import pandas as pd

from src.domain.services_interfaces.i_market_data_client import IMarketDataClient


class YFinanceMarketDataClient(IMarketDataClient):
    """
    IMarketDataClient arayüzünü yfinance ile implemente eden sınıf.

    Notlar:
      - yfinance.download() fonksiyonunda `end` tarihi EXCLUSIVE (hariç).
        Yani 2024-01-01 için veri istiyorsak: start=2024-01-01, end=2024-01-02.
      - BIST hisseleri için tipik ticker formatı: 'AKBNK.IS', 'ASELS.IS' vb.
    """

    def __init__(self, timeout: int = 10) -> None:
        self._timeout = timeout

    # ----------------- Yardımcı metotlar ----------------- #

    def _next_date(self, d: date) -> date:
        """Verilen tarihten bir gün sonrasını döner."""
        return d + timedelta(days=1)

    def _to_decimal(self, value) -> Decimal:
        """
        yfinance/pandas'dan gelen float/np.float tiplerini güvenli şekilde Decimal'e çevir.
        """
        return Decimal(str(float(value.squeeze())))


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

        df = yf.download(
            tickers=ticker,
            start=start,
            end=end,
            interval="1d",
            progress=False,
            auto_adjust=False,
            timeout=self._timeout,
        )

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

        start = price_date
        end = self._next_date(price_date)

        # yfinance: birden çok ticker'ı liste olarak da alıyor
        df = yf.download(
            tickers=list(tickers),
            start=start,
            end=end,
            interval="1d",
            progress=False,
            auto_adjust=False,
            timeout=self._timeout,
        )

        if df.empty:
            # Hiçbir veri yoksa direkt boş döneriz (service katmanı handle eder)
            return {}

        result: Dict[int, Decimal] = {}

        # İki durum var:
        # 1) Tek ticker: df.columns normal Index -> Close sütunu var
        # 2) Çoklu ticker: df.columns MultiIndex -> ('Close', 'AKBNK.IS') gibi

        if isinstance(df.columns, pd.MultiIndex):
            # Çoklu ticker
            # df: index = DatetimeIndex, columns = MultiIndex(levels: ['Adj Close','Close',...], tickers)
            # İlgili tek gün için satır: df.iloc[0]
            row = df.iloc[-1]

            for stock_id, ticker in zip(stock_ids, tickers):
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
                stock_id = stock_ids[0]
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

        yf_start = start_date
        yf_end = self._next_date(end_date)  # end exclusive

        df = yf.download(
            tickers=ticker,
            start=yf_start,
            end=yf_end,
            interval="1d",
            progress=False,
            auto_adjust=False,
            timeout=self._timeout,
        )

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

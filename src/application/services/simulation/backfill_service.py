# src/application/services/backfill_service.py

from __future__ import annotations

from datetime import date, timedelta
from typing import List

import yfinance as yf
import pandas as pd

from src.domain.models.daily_price import DailyPrice
from src.domain.ports.repositories.i_price_repo import IPriceRepository


class BackfillService:
    """
    Geçmişe yönelik fiyat verisi yönetim servisi.

    İki ana işlev:
        1. backfill_range: yfinance'den tarih aralığı için veri çeker ve DB'ye kaydeder
        2. delete_range: belirli tarih aralığındaki fiyat verilerini siler
    """

    def __init__(self, stock_repo, price_repo: IPriceRepository) -> None:
        self._stock_repo = stock_repo
        self._price_repo = price_repo

    def backfill_range(self, start_date: date, end_date: date) -> int:
        """
        Belirtilen tarih aralığı için yfinance'den veri çeker ve DB'ye kaydeder.

        Args:
            start_date: Başlangıç tarihi (dahil)
            end_date: Bitiş tarihi (dahil)

        Returns:
            Kaydedilen fiyat verisi sayısı
        """
        if start_date > end_date:
            raise ValueError("Başlangıç tarihi bitiş tarihinden sonra olamaz.")

        # Hisseleri al
        stocks = self._stock_repo.get_all_stocks()
        if not stocks:
            raise ValueError("Veritabanında kayıtlı hisse yok.")

        tickers = [s.ticker for s in stocks]
        stock_map = {s.ticker: s.id for s in stocks}

        # yfinance end_date'i dahil etmez, +1 gün ekle
        yf_end_date = end_date + timedelta(days=1)

        # Yahoo Finance'den indir
        try:
            df = yf.download(
                tickers,
                start=start_date,
                end=yf_end_date,
                group_by="ticker",
                auto_adjust=False,
                progress=False,
            )
        except Exception as e:
            raise RuntimeError(f"Yahoo Finance indirme hatası: {e}")

        if df.empty:
            return 0

        # Veriyi DailyPrice listesine dönüştür
        prices_to_save = self._parse_yfinance_data(df, tickers, stock_map)

        # DB'ye kaydet
        if prices_to_save:
            self._price_repo.upsert_daily_prices_bulk(prices_to_save)

        return len(prices_to_save)

    def delete_range(self, start_date: date, end_date: date) -> int:
        """
        Belirtilen tarih aralığındaki fiyat verilerini siler.

        Args:
            start_date: Başlangıç tarihi (dahil)
            end_date: Bitiş tarihi (dahil)

        Returns:
            Silinen kayıt sayısı
        """
        if start_date > end_date:
            raise ValueError("Başlangıç tarihi bitiş tarihinden sonra olamaz.")

        return self._price_repo.delete_prices_in_range(start_date, end_date)

    @staticmethod
    def _parse_yfinance_data(
        df: pd.DataFrame,
        tickers: List[str],
        stock_map: dict,
    ) -> List[DailyPrice]:
        """yfinance DataFrame'ini DailyPrice listesine dönüştürür."""
        prices = []
        is_multi_index = isinstance(df.columns, pd.MultiIndex)

        for ticker in tickers:
            stock_id = stock_map.get(ticker)
            if not stock_id:
                continue

            try:
                if is_multi_index:
                    if ticker not in df.columns.levels[0]:
                        continue
                    stock_data = df[ticker]
                else:
                    if len(tickers) == 1:
                        stock_data = df
                    else:
                        continue

                for timestamp, row in stock_data.iterrows():
                    close_val = row.get("Close")

                    if isinstance(close_val, pd.Series):
                        close_val = close_val.iloc[0]

                    if pd.isna(close_val):
                        continue

                    daily_price = DailyPrice(
                        id=None,
                        stock_id=stock_id,
                        price_date=timestamp.date(),
                        close_price=float(close_val),
                    )
                    prices.append(daily_price)

            except Exception:
                continue

        return prices

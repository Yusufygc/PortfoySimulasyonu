"""Backtest servisleri için ortak fiyat serisi okuyucu (DuckDB birincil, SQLite yedek)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, Iterable

PriceSeries = Dict[date, Dict[str, Decimal]]


def load_price_series(
    price_repo,
    stock_repo,
    market_history_repo,
    tickers: Iterable[str],
    start_date: date,
    end_date: date,
) -> PriceSeries:
    """tarih -> {ticker: kapanış}. Birincil kaynak DuckDB piyasa geçmişi (tüm BIST, sermaye artırımı düzeltmeli);
    DuckDB'de olmayan hisseler için SQLite portföy fiyatları kullanılır."""
    price_series: PriceSeries = {}
    for ticker in tickers:
        bars = market_history_repo.get_price_series(ticker, start_date, end_date) if market_history_repo is not None else []
        if bars:
            for bar in bars:
                price_series.setdefault(bar.price_date, {})[ticker] = Decimal(str(bar.close_price))
            continue

        stock = stock_repo.get_stock_by_ticker(ticker)
        if stock is None or stock.id is None:
            alt = ticker[:-3] if ticker.endswith(".IS") else f"{ticker}.IS"
            stock = stock_repo.get_stock_by_ticker(alt)
        if stock is not None and stock.id is not None:
            for row in price_repo.get_price_series(stock.id, start_date, end_date):
                price_series.setdefault(row.price_date, {})[ticker] = row.close_price
    return price_series

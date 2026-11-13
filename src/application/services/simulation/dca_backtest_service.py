"""
DCABacktestService — DCA backtest motorunun DB orkestrasyonu.

Sorumluluk:
- Verilen ticker listesi için fiyat serilerini local DB'den oku
- Ticker -> fiyat haritasına dönüştür, katkı tarihlerini belirle
- simulate_dca (saf) ile simülasyonu çalıştır, sonucu döndür
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

from src.application.services.simulation.dca_backtest import (
    DCABacktestResult,
    equal_weights,
    monthly_contribution_dates,
    simulate_dca,
)
from src.application.services.simulation.price_series_loader import load_price_series
from src.domain.ports.repositories.i_price_repo import IPriceRepository
from src.domain.ports.repositories.i_stock_repo import IStockRepository


class DCABacktestService:
    """'Her ay X TL alsaydım' senaryosunu yerel DB fiyat geçmişiyle çalıştırır."""

    def __init__(
        self,
        price_repo: IPriceRepository,
        stock_repo: IStockRepository,
        market_history_repo=None,
    ) -> None:
        self._price_repo = price_repo
        self._stock_repo = stock_repo
        # Portföyde (SQLite) olmayan hisseler için DuckDB piyasa geçmişi (opsiyonel)
        self._market_history_repo = market_history_repo

    def run(
        self,
        tickers: List[str],
        monthly_contribution: Decimal,
        start_date: date,
        end_date: date,
        weights: Optional[Dict[str, float]] = None,
    ) -> DCABacktestResult:
        """
        tickers: simüle edilecek hisseler (örn. ["AKBNK", "FROTO"]).
        weights: ticker -> pay (0-1). None ise eşit ağırlık kullanılır.
        """
        normalized_tickers = [t.strip().upper() for t in tickers]
        price_series = self._build_price_series(normalized_tickers, start_date, end_date)
        if not price_series:
            return simulate_dca({}, normalized_tickers, weights or {}, monthly_contribution, [])

        contribution_dates = monthly_contribution_dates(list(price_series.keys()))
        effective_weights = weights or equal_weights(normalized_tickers)

        return simulate_dca(
            price_series=price_series,
            tickers=normalized_tickers,
            weights=effective_weights,
            contribution_amount=monthly_contribution,
            contribution_dates=contribution_dates,
        )

    def _build_price_series(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date,
    ) -> Dict[date, Dict[str, Decimal]]:
        return load_price_series(
            self._price_repo, self._stock_repo, self._market_history_repo, tickers, start_date, end_date
        )

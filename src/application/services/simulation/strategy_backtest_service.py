"""
StrategyBacktestService — periyodik yeniden dengeleme ve stop-loss / take-profit backtest orkestrasyonu.

Sorumluluk:
- Girdileri doğrula (hisse sayısı, tutar, tarih aralığı, eşikler)
- Fiyat serisini DuckDB piyasa geçmişinden (yedek: SQLite) oku; Markowitz ağırlıkları için başlangıçtan önce ısınma verisi ekle
- strategy_backtest (saf) ile simülasyonu çalıştır

Markowitz ağırlığı: her yeniden dengeleme gününde, o güne kadarki son `lookback_days` günlük fiyatlardan maksimum Sharpe
(`compute_max_sharpe_weights`, tek hisse üst sınırı politika varsayılanıdır). Yalnızca o güne kadarki veri kullanılır
(ileriye bakış yok). Veri yetersizse o gün eşit ağırlığa dönülür ve olay listesine yazılır.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

import pandas as pd

from src.application.services.planning.optimization_service import compute_max_sharpe_weights
from src.application.services.simulation.price_series_loader import load_price_series
from src.application.services.simulation.strategy_backtest import (
    BacktestSetup,
    StrategyBacktestResult,
    equal_weight_function,
    simulate_rebalancing,
    simulate_stop_take,
)

WEIGHTING_EQUAL = "equal"
WEIGHTING_MARKOWITZ = "markowitz"

_MARKOWITZ_LOOKBACK_DAYS = 252
_WARMUP_CALENDAR_DAYS = 420  # 252 işlem günü + tatil payı
_MIN_HISTORY_ROWS = 60


def _normalize(tickers: List[str]) -> List[str]:
    seen: List[str] = []
    for ticker in tickers:
        clean = (ticker or "").strip().upper().replace(".IS", "")
        if clean and clean not in seen:
            seen.append(clean)
    return seen


def _validate_common(setup: BacktestSetup) -> None:
    if setup.initial_capital <= 0:
        raise ValueError("Başlangıç sermayesi 0'dan büyük olmalıdır.")
    if setup.end_date is None or setup.end_date <= setup.start_date:
        raise ValueError("Bitiş tarihi başlangıç tarihinden sonra olmalıdır.")
    if not 0 <= setup.commission_rate < 0.1:
        raise ValueError("Komisyon oranı %0 ile %10 arasında olmalıdır.")


class StrategyBacktestService:
    """Yeniden dengeleme ve stop-loss / take-profit stratejilerini yerel fiyat geçmişiyle çalıştırır."""

    def __init__(self, price_repo, stock_repo, market_history_repo=None) -> None:
        self._price_repo = price_repo
        self._stock_repo = stock_repo
        self._market_history_repo = market_history_repo

    def run_rebalancing(
        self,
        setup: BacktestSetup,
        rebalance_every_months: int = 3,
        weighting: str = WEIGHTING_EQUAL,
    ) -> StrategyBacktestResult:
        names = _normalize(list(setup.tickers))
        if len(names) < 2:
            raise ValueError("Yeniden dengeleme için en az 2 hisse kodu girin.")
        if weighting not in (WEIGHTING_EQUAL, WEIGHTING_MARKOWITZ):
            raise ValueError("Ağırlık yöntemi 'equal' veya 'markowitz' olmalıdır.")
        if not 1 <= rebalance_every_months <= 12:
            raise ValueError("Yeniden dengeleme aralığı 1 ile 12 ay arasında olmalıdır.")
        _validate_common(setup)

        warmup = _WARMUP_CALENDAR_DAYS if weighting == WEIGHTING_MARKOWITZ else 0
        series = self._load(names, setup.start_date - timedelta(days=warmup), setup.end_date)
        weight_fn = self._markowitz_weight_function() if weighting == WEIGHTING_MARKOWITZ else equal_weight_function(names)
        return simulate_rebalancing(series, replace(setup, tickers=names), rebalance_every_months, weight_fn)

    def run_stop_take(
        self,
        setup: BacktestSetup,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
    ) -> StrategyBacktestResult:
        names = _normalize(list(setup.tickers))
        if not names:
            raise ValueError("En az bir hisse kodu girin.")
        if stop_loss_pct is None and take_profit_pct is None:
            raise ValueError("Stop-loss veya take-profit eşiklerinden en az birini girin.")
        for label, value in (("Stop-loss", stop_loss_pct), ("Take-profit", take_profit_pct)):
            if value is not None and value <= 0:
                raise ValueError(f"{label} eşiği 0'dan büyük olmalıdır.")
        if stop_loss_pct is not None and stop_loss_pct >= 100:
            raise ValueError("Stop-loss eşiği %100'den küçük olmalıdır.")
        _validate_common(setup)

        series = self._load(names, setup.start_date, setup.end_date)
        return simulate_stop_take(series, replace(setup, tickers=names), stop_loss_pct, take_profit_pct)

    def _load(self, tickers: List[str], start_date: date, end_date: date) -> Dict[date, Dict[str, Decimal]]:
        series = load_price_series(
            self._price_repo, self._stock_repo, self._market_history_repo, tickers, start_date, end_date
        )
        if not series:
            raise ValueError("Seçilen hisseler için fiyat verisi bulunamadı.")
        return series

    @staticmethod
    def _markowitz_weight_function():
        def weights(_as_of: date, history: pd.DataFrame) -> Dict[str, float]:
            window = history.tail(_MARKOWITZ_LOOKBACK_DAYS + 1)
            usable = [c for c in window.columns if window[c].notna().sum() >= _MIN_HISTORY_ROWS]
            if len(usable) < 2:
                raise ValueError("yeterli fiyat geçmişi olan en az 2 hisse yok")
            computed = compute_max_sharpe_weights(window[usable].dropna())
            return {ticker: computed.get(ticker, 0.0) for ticker in window.columns}

        return weights

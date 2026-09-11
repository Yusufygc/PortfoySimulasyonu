"""
Stock360Service — "Hisse 360" birleşik servisi (bkz. plan §5.1).

FinancialsPage/ShareholdersPage/StockDetailPage'in ayrık servis çağrılarını
tek bir giriş noktasında toplar:
  1. Genel Bakış  — son fiyat, günlük değişim, hacim, 52 haftalık aralık (lokal DB).
  2. Teknik Seviyeler — RSI/MACD/SMA/EMA ve destek/direnç (lokal DB).
  3. Temel Finansallar — İş Yatırım bilanço/oran verisi (dış API, FinancialAnalysisService).
  4. Ortaklık Yapısı — KAP pay sahipliği (dış API, ShareholderAnalysisService).

Genel Bakış ve Teknik Seviyeler yalnızca `price_repo` okur (canlı API çağrısı
yapmaz — Screener'daki §9.6 önkoşuluyla aynı prensip). Finansallar/Ortaklık
dış API'ye gittiği için `get_snapshot()` içinde birbirinden izole edilir:
biri hata verse diğer boyutlar etkilenmez.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, List, Optional

import pandas as pd

from src.application.services.analysis.financial_analysis_service import FinancialAnalysisService
from src.application.services.analysis.shareholder_analysis_service import ShareholderAnalysisService
from src.application.services.analysis.technical.indicators import ema, macd, rsi, sma
from src.application.services.analysis.technical.support_resistance import compute_support_resistance
from src.domain.models.daily_price import DailyPrice
from src.domain.models.shareholder import ShareholderSnapshot
from src.domain.ports.repositories.i_price_repo import IPriceRepository
from src.domain.ports.repositories.i_stock_repo import IStockRepository

logger = logging.getLogger(__name__)

# 52 haftalık aralık + SMA200 ısınma payı için ~1.15 yıllık lokal veri.
_OVERVIEW_LOOKBACK_DAYS = 420
_SMA_SHORT, _SMA_LONG, _EMA_SHORT = 50, 200, 20


@dataclass(frozen=True)
class StockOverview:
    """Genel Bakış anlık görüntüsü (plan §5.1 madde 1)."""
    ticker: str
    last_price: Decimal
    last_price_date: date
    daily_change_pct: Optional[float]
    volume: Optional[int]
    week52_low: Decimal
    week52_high: Decimal


@dataclass(frozen=True)
class TechnicalLevels:
    """Teknik Seviyeler anlık görüntüsü (plan §5.1 madde 4)."""
    ticker: str
    rsi14: Optional[float]
    macd_line: Optional[float]
    macd_signal: Optional[float]
    sma50: Optional[float]
    sma200: Optional[float]
    ema20: Optional[float]
    support: Optional[float]
    resistance: Optional[float]


@dataclass(frozen=True)
class Stock360Snapshot:
    """`get_snapshot()` birleşik dönüş paketi — Gemini tool-calling için de kullanılabilir (bkz. §6.2)."""
    ticker: str
    overview: Optional[StockOverview]
    technical: Optional[TechnicalLevels]
    financials: Optional[dict[str, Any]]
    financials_error: Optional[str]
    shareholders: List[ShareholderSnapshot]
    shareholders_error: Optional[str]


def _rows_to_series(rows: List[DailyPrice], field: str) -> pd.Series:
    dates = [r.price_date for r in rows]
    values = [float(getattr(r, field)) if getattr(r, field) is not None else float("nan") for r in rows]
    return pd.Series(values, index=dates)


def _last_float(series: pd.Series) -> Optional[float]:
    if len(series) == 0 or pd.isna(series.iloc[-1]):
        return None
    return float(series.iloc[-1])


class Stock360Service:
    """Hisse 360 görünümü — Genel Bakış/TA (lokal, hızlı) + Finansallar/Ortaklık (dış API, izole)."""

    def __init__(
        self,
        price_repo: IPriceRepository,
        stock_repo: IStockRepository,
        financial_analysis_service: FinancialAnalysisService,
        shareholder_analysis_service: ShareholderAnalysisService,
    ) -> None:
        self._price_repo = price_repo
        self._stock_repo = stock_repo
        self._financial_service = financial_analysis_service
        self._shareholder_service = shareholder_analysis_service

    # ------------------------------------------------------------------
    # Genel Bakış + Teknik Seviyeler (lokal DB)
    # ------------------------------------------------------------------

    def get_overview(self, ticker: str, today: Optional[date] = None) -> Optional[StockOverview]:
        rows = self._load_recent_prices(ticker, today)
        if not rows:
            return None
        last = rows[-1]
        prev_close = float(rows[-2].close_price) if len(rows) >= 2 else None
        change_pct = (
            (float(last.close_price) - prev_close) / prev_close * 100.0
            if prev_close not in (None, 0.0)
            else None
        )
        week52_start = last.price_date - timedelta(days=365)
        week52_closes = [r.close_price for r in rows if r.price_date >= week52_start] or [last.close_price]
        return StockOverview(
            ticker=ticker.strip().upper(),
            last_price=last.close_price,
            last_price_date=last.price_date,
            daily_change_pct=change_pct,
            volume=last.volume,
            week52_low=min(week52_closes),
            week52_high=max(week52_closes),
        )

    def get_technical_levels(self, ticker: str, today: Optional[date] = None) -> Optional[TechnicalLevels]:
        rows = self._load_recent_prices(ticker, today)
        if len(rows) < 20:
            return None
        closes = _rows_to_series(rows, "close_price")
        highs = _rows_to_series(rows, "high_price")
        lows = _rows_to_series(rows, "low_price")

        rsi_series = rsi(closes)
        macd_line, macd_signal, _ = macd(closes)
        support, resistance = compute_support_resistance(highs, lows, closes)

        return TechnicalLevels(
            ticker=ticker.strip().upper(),
            rsi14=_last_float(rsi_series),
            macd_line=_last_float(macd_line),
            macd_signal=_last_float(macd_signal),
            sma50=_last_float(sma(closes, _SMA_SHORT)),
            sma200=_last_float(sma(closes, _SMA_LONG)),
            ema20=_last_float(ema(closes, _EMA_SHORT)),
            support=support,
            resistance=resistance,
        )

    # ------------------------------------------------------------------
    # Temel Finansallar (İş Yatırım, dış API)
    # ------------------------------------------------------------------

    def get_financials(self, ticker: str, n_quarters: int = 12, currency: str = "TRY") -> dict[str, Any]:
        return self._financial_service.analyze(ticker, n_quarters=n_quarters, currency=currency)

    # ------------------------------------------------------------------
    # Ortaklık Yapısı (KAP, dış API)
    # ------------------------------------------------------------------

    def get_shareholders(self, ticker: str, force_refresh: bool = False) -> List[ShareholderSnapshot]:
        return self._shareholder_service.get_history(ticker, force_refresh=force_refresh)

    # ------------------------------------------------------------------
    # Birleşik anlık görüntü — 4 boyut, dış API hataları izole edilir.
    # ------------------------------------------------------------------

    def get_snapshot(self, ticker: str, today: Optional[date] = None) -> Stock360Snapshot:
        ticker_norm = ticker.strip().upper()
        overview = self.get_overview(ticker_norm, today)
        technical = self.get_technical_levels(ticker_norm, today)

        financials: Optional[dict[str, Any]] = None
        financials_error: Optional[str] = None
        try:
            financials = self.get_financials(ticker_norm)
        except Exception as exc:
            logger.warning("Stock360Service.get_snapshot: finansal veri alınamadı [%s]: %s", ticker_norm, exc)
            financials_error = str(exc)

        shareholders: List[ShareholderSnapshot] = []
        shareholders_error: Optional[str] = None
        try:
            shareholders = self.get_shareholders(ticker_norm)
        except Exception as exc:
            logger.warning("Stock360Service.get_snapshot: ortaklık verisi alınamadı [%s]: %s", ticker_norm, exc)
            shareholders_error = str(exc)

        return Stock360Snapshot(
            ticker=ticker_norm,
            overview=overview,
            technical=technical,
            financials=financials,
            financials_error=financials_error,
            shareholders=shareholders,
            shareholders_error=shareholders_error,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load_recent_prices(self, ticker: str, today: Optional[date]) -> List[DailyPrice]:
        today = today or date.today()
        stock = self._stock_repo.get_stock_by_ticker(ticker.strip().upper())
        if stock is None or stock.id is None:
            return []
        start = today - timedelta(days=_OVERVIEW_LOOKBACK_DAYS)
        rows = self._price_repo.get_price_series(stock.id, start, today)
        return sorted(rows, key=lambda r: r.price_date)

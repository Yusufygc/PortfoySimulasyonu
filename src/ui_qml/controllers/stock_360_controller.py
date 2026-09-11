"""
Stock360Controller — Stock360View'un veri köprüsü (bkz. plan §7.3 madde 2, d2).

3 sekmeye veri sağlar:
  1. Fiyat Grafiği & Canlı İndikatörler — mum grafik + RSI/MACD alt panel. Lokal
     `price_repo` + `indicators.py` (rsi/macd) pure fonksiyonları ile hesaplanır
     (zaman aralığı seçici: 1G/1H/1A/3A/1Y/5Y — bkz. `_RANGE_LOOKBACK_DAYS`).
  2. Bilanço & Rasyolar — `Stock360Service.get_financials()`'e delege, rasyo rozetleri
     (F/K, PD/DD, FD/FAVÖK, ROE) `financials/valuation.py` ve `metrics.py` çıktısından.
  3. Ortaklık Yapısı (KAP) — `Stock360Service.get_shareholders()`'e delege.

Genel Bakış (son fiyat, günlük %, hacim, 52 hafta) ve anlık Teknik Seviyeler
(RSI14/MACD/SMA/EMA/destek-direnç) `Stock360Service.get_overview()`/
`get_technical_levels()`'e delege edilir (§5.1) — hesap mantığı yeniden yazılmadı.

Finansallar ve Ortaklık Yapısı dış API'ye gider (İş Yatırım/KAP) — hata durumunda
o boyutun eski verisi/sıfır değerleri kalır ve `*Error` property'si set edilir;
fiyat/teknik/diğer sekmeleri etkilemez (bkz. Stock360Service docstring'i, §5.1).
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

from src.qt_compat.qtcore import Property, QObject, Signal, Slot
from src.application.services.analysis.technical.indicators import macd, rsi
from src.domain.models.daily_price import DailyPrice

logger = logging.getLogger(__name__)

_RANGE_LOOKBACK_DAYS: Dict[str, int] = {"1G": 5, "1H": 7, "1A": 30, "3A": 90, "1Y": 365, "5Y": 1825}
_DEFAULT_RANGE_KEY = "3A"
# RSI14 (14) + MACD(12,26,9) isinmasi icin en buyuk lookback'in ustune ek pay.
_WARMUP_DAYS = 280


def _rows_to_series(rows: List[DailyPrice], field: str) -> pd.Series:
    return pd.Series(
        [float(getattr(r, field)) if getattr(r, field) is not None else float("nan") for r in rows]
    )


def _tail_values(series: pd.Series, start_index: int) -> List[float]:
    """NaN'lari 0.0'a indirger (isinma donemi disinda kalmis olmasi beklenir)."""
    return [0.0 if pd.isna(v) else float(v) for v in series.iloc[start_index:]]


def _to_float(value: Any) -> float:
    return float(value) if value is not None else 0.0


class Stock360Controller(QObject):
    """Tek bir hisse için Genel Bakış/TA/Finansallar/Ortaklık verisini QML'e sunar."""

    tickerChanged = Signal()
    notFoundChanged = Signal()
    rangeKeyChanged = Signal()
    overviewChanged = Signal()
    technicalChanged = Signal()
    priceSeriesChanged = Signal()
    financialsChanged = Signal()
    shareholdersChanged = Signal()

    def __init__(self, container, parent=None) -> None:
        super().__init__(parent)
        self._container = container
        self._ticker = ""
        self._not_found = False
        self._range_key = _DEFAULT_RANGE_KEY

        self._last_price = 0.0
        self._daily_change_pct = 0.0
        self._volume = 0
        self._week52_low = 0.0
        self._week52_high = 0.0

        self._rsi14 = 0.0
        self._macd_line = 0.0
        self._macd_signal = 0.0
        self._sma50 = 0.0
        self._sma200 = 0.0
        self._ema20 = 0.0
        self._support = 0.0
        self._resistance = 0.0

        self._candlestick_bars: List[Dict[str, float]] = []
        self._rsi_series: List[float] = []
        self._macd_line_series: List[float] = []
        self._macd_signal_series: List[float] = []

        self._financials_error: Optional[str] = None
        self._fk = 0.0
        self._pddd = 0.0
        self._ev_favok = 0.0
        self._roe = 0.0
        self._financial_period = ""

        self._shareholders_error: Optional[str] = None
        self._shareholder_names: List[str] = []
        self._shareholder_ratios: List[float] = []
        self._free_float_pct = 0.0
        self._shareholder_snapshot_count = 0

    # ------------------------------------------------------------------
    # Ticker / zaman aralığı
    # ------------------------------------------------------------------

    @Property(str, notify=tickerChanged)
    def ticker(self) -> str:
        return self._ticker

    @Property(bool, notify=notFoundChanged)
    def notFound(self) -> bool:
        return self._not_found

    @Property(str, notify=rangeKeyChanged)
    def rangeKey(self) -> str:
        return self._range_key

    @Property("QVariantList", constant=True)
    def rangeKeys(self) -> List[str]:
        return list(_RANGE_LOOKBACK_DAYS.keys())

    @Slot(str)
    def loadTicker(self, ticker: str) -> None:
        """Arama kutusundan çağrılır — ticker'ı normalize eder ve tüm boyutları yükler."""
        ticker = (ticker or "").strip().upper()
        if not ticker:
            return
        self._ticker = ticker
        self.tickerChanged.emit()
        self.refresh()

    @Slot(str)
    def setRangeKey(self, range_key: str) -> None:
        if range_key not in _RANGE_LOOKBACK_DAYS or range_key == self._range_key:
            return
        self._range_key = range_key
        self.rangeKeyChanged.emit()
        self._refresh_price_and_indicators()

    # ------------------------------------------------------------------
    # Sekme 1: Genel Bakış + Teknik Seviyeler (anlık değerler)
    # ------------------------------------------------------------------

    @Property(float, notify=overviewChanged)
    def lastPrice(self) -> float:
        return self._last_price

    @Property(float, notify=overviewChanged)
    def dailyChangePct(self) -> float:
        return self._daily_change_pct

    @Property(int, notify=overviewChanged)
    def volume(self) -> int:
        return self._volume

    @Property(float, notify=overviewChanged)
    def week52Low(self) -> float:
        return self._week52_low

    @Property(float, notify=overviewChanged)
    def week52High(self) -> float:
        return self._week52_high

    @Property(float, notify=technicalChanged)
    def rsi14(self) -> float:
        return self._rsi14

    @Property(float, notify=technicalChanged)
    def macdLine(self) -> float:
        return self._macd_line

    @Property(float, notify=technicalChanged)
    def macdSignal(self) -> float:
        return self._macd_signal

    @Property(float, notify=technicalChanged)
    def sma50(self) -> float:
        return self._sma50

    @Property(float, notify=technicalChanged)
    def sma200(self) -> float:
        return self._sma200

    @Property(float, notify=technicalChanged)
    def ema20(self) -> float:
        return self._ema20

    @Property(float, notify=technicalChanged)
    def support(self) -> float:
        return self._support

    @Property(float, notify=technicalChanged)
    def resistance(self) -> float:
        return self._resistance

    # ------------------------------------------------------------------
    # Sekme 1: Mum grafiği + RSI/MACD serileri (zaman aralığına bağlı)
    # ------------------------------------------------------------------

    @Property("QVariantList", notify=priceSeriesChanged)
    def candlestickBars(self) -> List[Dict[str, float]]:
        return list(self._candlestick_bars)

    @Property("QVariantList", notify=priceSeriesChanged)
    def rsiSeries(self) -> List[float]:
        return list(self._rsi_series)

    @Property("QVariantList", notify=priceSeriesChanged)
    def macdLineSeries(self) -> List[float]:
        return list(self._macd_line_series)

    @Property("QVariantList", notify=priceSeriesChanged)
    def macdSignalSeries(self) -> List[float]:
        return list(self._macd_signal_series)

    # ------------------------------------------------------------------
    # Sekme 2: Bilanço & Rasyolar
    # ------------------------------------------------------------------

    @Property(str, notify=financialsChanged)
    def financialsError(self) -> str:
        return self._financials_error or ""

    @Property(float, notify=financialsChanged)
    def fk(self) -> float:
        return self._fk

    @Property(float, notify=financialsChanged)
    def pddd(self) -> float:
        return self._pddd

    @Property(float, notify=financialsChanged)
    def evFavok(self) -> float:
        return self._ev_favok

    @Property(float, notify=financialsChanged)
    def roe(self) -> float:
        return self._roe

    @Property(str, notify=financialsChanged)
    def financialPeriod(self) -> str:
        return self._financial_period

    # ------------------------------------------------------------------
    # Sekme 3: Ortaklık Yapısı (KAP)
    # ------------------------------------------------------------------

    @Property(str, notify=shareholdersChanged)
    def shareholdersError(self) -> str:
        return self._shareholders_error or ""

    @Property("QVariantList", notify=shareholdersChanged)
    def shareholderNames(self) -> List[str]:
        return list(self._shareholder_names)

    @Property("QVariantList", notify=shareholdersChanged)
    def shareholderRatios(self) -> List[float]:
        return list(self._shareholder_ratios)

    @Property(float, notify=shareholdersChanged)
    def freeFloatPct(self) -> float:
        return self._free_float_pct

    @Property(int, notify=shareholdersChanged)
    def shareholderSnapshotCount(self) -> int:
        return self._shareholder_snapshot_count

    # ------------------------------------------------------------------
    # Veri yenileme
    # ------------------------------------------------------------------

    @Slot()
    def refresh(self) -> None:
        if not self._ticker:
            return
        self._refresh_overview_and_technical()
        self._refresh_price_and_indicators()
        self._refresh_financials()
        self._refresh_shareholders()

    def _refresh_overview_and_technical(self) -> None:
        service = self._container.stock_360_service
        overview = service.get_overview(self._ticker)
        technical = service.get_technical_levels(self._ticker)
        self._not_found = overview is None
        self.notFoundChanged.emit()
        if overview is not None:
            self._last_price = _to_float(overview.last_price)
            self._daily_change_pct = _to_float(overview.daily_change_pct)
            self._volume = int(overview.volume) if overview.volume is not None else 0
            self._week52_low = _to_float(overview.week52_low)
            self._week52_high = _to_float(overview.week52_high)
        self.overviewChanged.emit()

        if technical is not None:
            self._rsi14 = _to_float(technical.rsi14)
            self._macd_line = _to_float(technical.macd_line)
            self._macd_signal = _to_float(technical.macd_signal)
            self._sma50 = _to_float(technical.sma50)
            self._sma200 = _to_float(technical.sma200)
            self._ema20 = _to_float(technical.ema20)
            self._support = _to_float(technical.support)
            self._resistance = _to_float(technical.resistance)
        self.technicalChanged.emit()

    def _refresh_price_and_indicators(self) -> None:
        rows = self._load_rows_with_warmup()
        if not rows:
            self._candlestick_bars = []
            self._rsi_series = []
            self._macd_line_series = []
            self._macd_signal_series = []
            self.priceSeriesChanged.emit()
            return

        visible_start_index = self._visible_start_index(rows)
        closes = _rows_to_series(rows, "close_price")
        rsi_series = rsi(closes)
        macd_line_series, macd_signal_series, _ = macd(closes)

        self._rsi_series = _tail_values(rsi_series, visible_start_index)
        self._macd_line_series = _tail_values(macd_line_series, visible_start_index)
        self._macd_signal_series = _tail_values(macd_signal_series, visible_start_index)
        self._candlestick_bars = self._build_candlestick_bars(rows[visible_start_index:])
        self.priceSeriesChanged.emit()

    def _refresh_financials(self) -> None:
        self._financials_error = None
        try:
            metrics = self._container.stock_360_service.get_financials(self._ticker)
        except Exception as exc:
            logger.warning("Stock360Controller: finansal veri alınamadı [%s]: %s", self._ticker, exc)
            self._financials_error = str(exc)
            self.financialsChanged.emit()
            return

        periods = metrics.get("periods") or []
        period = periods[0] if periods else None
        market_val = metrics.get("_market_val") or {}
        self._fk = _to_float(market_val.get("fk"))
        self._pddd = _to_float(market_val.get("pddd"))
        self._ev_favok = _to_float(market_val.get("ev_favok"))
        self._roe = _to_float(metrics.get("roe", {}).get(period)) if period else 0.0
        self._financial_period = period or ""
        self.financialsChanged.emit()

    def _refresh_shareholders(self) -> None:
        self._shareholders_error = None
        try:
            snapshots = self._container.stock_360_service.get_shareholders(self._ticker)
        except Exception as exc:
            logger.warning("Stock360Controller: ortaklık verisi alınamadı [%s]: %s", self._ticker, exc)
            self._shareholders_error = str(exc)
            self.shareholdersChanged.emit()
            return

        self._shareholder_snapshot_count = len(snapshots)
        if not snapshots:
            self._shareholder_names = []
            self._shareholder_ratios = []
            self._free_float_pct = 0.0
            self.shareholdersChanged.emit()
            return

        latest = max(snapshots, key=lambda s: s.creation_date)
        named_rows = [r for r in latest.rows if not r.is_total]
        self._shareholder_names = [r.shareholder_name for r in named_rows]
        self._shareholder_ratios = [_to_float(r.ratio_in_capital) for r in named_rows]
        known_pct = sum(self._shareholder_ratios)
        self._free_float_pct = max(0.0, 100.0 - known_pct)
        self.shareholdersChanged.emit()

    # ------------------------------------------------------------------
    # Internals — fiyat/indikatör serisi yükleme
    # ------------------------------------------------------------------

    def _load_rows_with_warmup(self) -> List[DailyPrice]:
        stock = self._container.stock_repo.get_stock_by_ticker(self._ticker)
        if stock is None or stock.id is None:
            return []
        today = date.today()
        lookback_days = _RANGE_LOOKBACK_DAYS[self._range_key]
        start = today - timedelta(days=lookback_days + _WARMUP_DAYS)
        rows = self._container.price_repo.get_price_series(stock.id, start, today)
        return sorted(rows, key=lambda r: r.price_date)

    def _visible_start_index(self, rows: List[DailyPrice]) -> int:
        """Görünür pencereyi DB'deki EN SON satırın tarihine göre sabitler — literal
        `date.today()`'e göre değil. Aksi halde veri güncelliği geride kalmış (stale)
        bir hissede (bkz. plan §9.12 ticker/veri güncelliği bulgusu) pencere neredeyse
        tamamen veri olmayan güncel tarihlere denk gelir ve tek bar kalır."""
        lookback_days = _RANGE_LOOKBACK_DAYS[self._range_key]
        latest_available_date = rows[-1].price_date
        visible_start_date = latest_available_date - timedelta(days=lookback_days)
        for index, row in enumerate(rows):
            if row.price_date >= visible_start_date:
                return index
        return 0

    @staticmethod
    def _build_candlestick_bars(rows: List[DailyPrice]) -> List[Dict[str, float]]:
        bars = []
        for row in rows:
            if row.open_price is None or row.high_price is None or row.low_price is None:
                continue
            bars.append({
                "open": float(row.open_price),
                "high": float(row.high_price),
                "low": float(row.low_price),
                "close": float(row.close_price),
            })
        return bars

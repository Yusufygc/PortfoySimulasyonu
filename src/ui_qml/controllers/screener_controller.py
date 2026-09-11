"""
ScreenerController — ScreenerView'un veri köprüsü (bkz. plan §7.3 madde 3, d3).

Üst çubuk hazır filtre çipleri = mevcut `SCREENER_FILTERS` kayıt defterindeki 3
filtre (RSI aşırı satım+EMA200 üzeri, MACD bullish kesişim+hacim patlaması,
Bollinger alt bant değme). Plan'ın orijinal metni 4 ayrı çip öneriyordu (RSI<30,
MACD bullish, EMA200 üzeri, Hacim patlaması ayrı ayrı) ama gerçek `screener.py`
bunlardan ikisini (RSI+EMA200, MACD+Hacim) birleşik tek filtre olarak tanımlıyor
— burada var olan 3 filtreye sadık kalındı, yeni bir filtre icat edilmedi.

Tarama `ScreenerService.scan()`'e delege edilir — SADECE lokal DB okur, canlı API
çağrısı yapmaz (§9.6). Satır seçildiğinde mini özet + sparkline için
`Stock360Service`/`price_repo`'ya delege edilir (§5.1), yeniden hesaplama yapılmaz.

"Trend rozeti" notu: `SCREENER_FILTERS`'daki 3 filtrenin üçü de bullish (giriş)
sinyali tanımlıyor — şu an sistemde bearish/"Ayı" sinyali üreten bir filtre yok.
Bu yüzden eşleşen her satır dürüstçe "Boğa" etiketlenir (icat edilmiş bir
sınıflandırma değil, mevcut filtrelerin gerçek anlamı) — bearish filtre ileride
`screener.py`'ye eklenirse bu etiket de genişletilebilir.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, List

from src.qt_compat.qtcore import Property, QObject, Signal, Slot
from src.application.services.analysis.technical.screener import SCREENER_FILTERS

_SPARKLINE_LOOKBACK_DAYS = 90
_TREND_BULLISH = "Boğa"


def _to_float(value: Any) -> float:
    return float(value) if value is not None else 0.0


class ScreenerController(QObject):
    """BIST çoklu sinyal tarayıcısı — filtre çipleri + sonuç listesi + mini özet paneli."""

    activeFiltersChanged = Signal()
    resultsChanged = Signal()
    selectedTickerChanged = Signal()
    miniOverviewChanged = Signal()
    sparklineChanged = Signal()

    def __init__(self, container, parent=None) -> None:
        super().__init__(parent)
        self._container = container
        self._active_filters: List[str] = list(SCREENER_FILTERS.keys())

        self._result_tickers: List[str] = []
        self._result_filter_labels: List[str] = []
        self._result_close_prices: List[float] = []
        self._result_trends: List[str] = []

        self._selected_ticker = ""
        self._mini_last_price = 0.0
        self._mini_rsi14 = 0.0
        self._mini_macd_line = 0.0
        self._mini_macd_signal = 0.0
        self._sparkline_values: List[float] = []

        self.runScan()

    # ------------------------------------------------------------------
    # Filtre çipleri
    # ------------------------------------------------------------------

    @Property("QVariantList", constant=True)
    def filterKeys(self) -> List[str]:
        return list(SCREENER_FILTERS.keys())

    @Property("QVariantList", constant=True)
    def filterLabels(self) -> List[str]:
        return [definition.label for definition in SCREENER_FILTERS.values()]

    @Property("QVariantList", notify=activeFiltersChanged)
    def activeFilters(self) -> List[str]:
        return list(self._active_filters)

    @Slot(str)
    def toggleFilter(self, filter_key: str) -> None:
        if filter_key not in SCREENER_FILTERS:
            return
        if filter_key in self._active_filters:
            self._active_filters.remove(filter_key)
        else:
            self._active_filters.append(filter_key)
        self.activeFiltersChanged.emit()
        self.runScan()

    # ------------------------------------------------------------------
    # Sonuç tablosu
    # ------------------------------------------------------------------

    @Property("QVariantList", notify=resultsChanged)
    def resultTickers(self) -> List[str]:
        return list(self._result_tickers)

    @Property("QVariantList", notify=resultsChanged)
    def resultFilterLabels(self) -> List[str]:
        return list(self._result_filter_labels)

    @Property("QVariantList", notify=resultsChanged)
    def resultClosePrices(self) -> List[float]:
        return list(self._result_close_prices)

    @Property("QVariantList", notify=resultsChanged)
    def resultTrends(self) -> List[str]:
        return list(self._result_trends)

    @Slot()
    def runScan(self) -> None:
        matches = self._container.screener_service.scan(filter_keys=list(self._active_filters))
        self._result_tickers = [m.ticker for m in matches]
        self._result_filter_labels = [m.filter_label for m in matches]
        self._result_close_prices = [_to_float(m.close_price) for m in matches]
        self._result_trends = [_TREND_BULLISH for _ in matches]
        self.resultsChanged.emit()

    # ------------------------------------------------------------------
    # Satır seçimi — mini özet + sparkline
    # ------------------------------------------------------------------

    @Property(str, notify=selectedTickerChanged)
    def selectedTicker(self) -> str:
        return self._selected_ticker

    @Property(float, notify=miniOverviewChanged)
    def miniLastPrice(self) -> float:
        return self._mini_last_price

    @Property(float, notify=miniOverviewChanged)
    def miniRsi14(self) -> float:
        return self._mini_rsi14

    @Property(float, notify=miniOverviewChanged)
    def miniMacdLine(self) -> float:
        return self._mini_macd_line

    @Property(float, notify=miniOverviewChanged)
    def miniMacdSignal(self) -> float:
        return self._mini_macd_signal

    @Property("QVariantList", notify=sparklineChanged)
    def sparklineValues(self) -> List[float]:
        return list(self._sparkline_values)

    @Slot(str)
    def selectTicker(self, ticker: str) -> None:
        ticker = (ticker or "").strip().upper()
        if not ticker:
            return
        self._selected_ticker = ticker
        self.selectedTickerChanged.emit()
        self._refresh_mini_overview(ticker)
        self._refresh_sparkline(ticker)

    def _refresh_mini_overview(self, ticker: str) -> None:
        service = self._container.stock_360_service
        overview = service.get_overview(ticker)
        technical = service.get_technical_levels(ticker)
        self._mini_last_price = _to_float(overview.last_price) if overview else 0.0
        self._mini_rsi14 = _to_float(technical.rsi14) if technical else 0.0
        self._mini_macd_line = _to_float(technical.macd_line) if technical else 0.0
        self._mini_macd_signal = _to_float(technical.macd_signal) if technical else 0.0
        self.miniOverviewChanged.emit()

    def _refresh_sparkline(self, ticker: str) -> None:
        stock = self._container.stock_repo.get_stock_by_ticker(ticker)
        if stock is None or stock.id is None:
            self._sparkline_values = []
            self.sparklineChanged.emit()
            return
        # Geniş bir pencere çekilip EN SON satırın tarihine göre kuyruk alınır —
        # literal `date.today()`'e göre kesilirse veri güncelliği geride kalmış
        # (stale, bkz. §9.12) bir hissede pencere neredeyse boş kalır (bkz.
        # Stock360Controller._visible_start_index'teki aynı düzeltme).
        today = date.today()
        wide_start = today - timedelta(days=_SPARKLINE_LOOKBACK_DAYS + 365)
        rows = sorted(
            self._container.price_repo.get_price_series(stock.id, wide_start, today),
            key=lambda r: r.price_date,
        )
        if not rows:
            self._sparkline_values = []
            self.sparklineChanged.emit()
            return

        visible_start_date = rows[-1].price_date - timedelta(days=_SPARKLINE_LOOKBACK_DAYS)
        visible_rows = [r for r in rows if r.price_date >= visible_start_date]
        self._sparkline_values = [_to_float(r.close_price) for r in visible_rows]
        self.sparklineChanged.emit()

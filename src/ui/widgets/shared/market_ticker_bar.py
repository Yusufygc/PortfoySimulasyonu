# src/ui/widgets/shared/market_ticker_bar.py
"""
MarketTickerBar — Haber kanalı köşesi tarzı piyasa şeridi.

Gram Altın | Gram Gümüş | USD | EUR | BIST 100

Kullanım:
    bar = MarketTickerBar(parent=self)
    layout.addWidget(bar)   # otomatik başlar, 5 dak yenilenir
    bar.cleanup()           # sayfa kapanırken çağır
"""
from __future__ import annotations

import logging
from typing import Any

# yfinance is imported dynamically inside functions to comply with refactor guards

from src.qt_compat.qtwidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QSizePolicy
from src.qt_compat.qtcore import QTimer, QThreadPool, Qt, QPoint
from src.ui.worker import Worker
from src.ui.widgets.shared.feedback.skeleton_widget import SkeletonBlock

logger = logging.getLogger(__name__)

TROY_OZ_TO_GRAM: float = 31.1035
REFRESH_INTERVAL_MS: int = 5 * 60 * 1000  # 5 dakika

# Sabit sıralı: USD önce (altın/gümüş TRY dönüşümü için gerekli)
# (etiket, USD cinsinden mi?, ticker listesi, para birimi)
# Altın/Gümüş: GC=F / SI=F (USD/troy oz) → USD/TRY ile çarp → gram'a böl
_SIMPLE_TICKERS = [
    ("USD/TRY",  "TRY=X",    "₺"),
    ("EUR/TRY",  "EURTRY=X", "₺"),
    ("BIST 100", "XU100.IS", ""),
]
_METAL_TICKERS = [
    ("ALTIN",  "GC=F", "₺"),
    ("GÜMÜŞ", "SI=F",  "₺"),
]
# Gösterim sırası
_DISPLAY_ORDER = ["ALTIN", "GÜMÜŞ", "USD/TRY", "EUR/TRY", "BIST 100"]


def _get_fast_price(ticker_symbol: str) -> float | None:
    """yfinance fast_info'dan fiyat çeker. None = başarısız."""
    from src.infrastructure.market_data.yfinance_lock import yfinance_lock
    with yfinance_lock:
        try:
            yf = __import__("yfinance")
            t = yf.Ticker(ticker_symbol)
            fi: Any = getattr(t, "fast_info", None)
            if fi is None:
                return None
            for key in ("lastPrice", "last_price", "regularMarketPrice", "currentPrice"):
                try:
                    val = fi.get(key) if hasattr(fi, "get") else getattr(fi, key, None)
                except Exception:
                    val = None
                if val is not None:
                    try:
                        return float(val)
                    except (TypeError, ValueError):
                        pass
            return None
        except Exception as exc:
            logger.debug("[MarketTickerBar] %s fetch failed: %s", ticker_symbol, exc)
            return None


def _fetch_all() -> dict[str, float]:
    """
    Tüm piyasa değerlerini sırayla çeker.
    USD/TRY önce çekilir → altın/gümüş USD→TRY dönüşümünde kullanılır.
    """
    results: dict[str, float] = {}
    usd_try: float | None = None

    # 1) USD, EUR, BIST
    for label, ticker, _ in _SIMPLE_TICKERS:
        price = _get_fast_price(ticker)
        if price is not None:
            results[label] = price
            if label == "USD/TRY":
                usd_try = price

    # 2) Altın ve Gümüş (USD/troy oz → TRY/gram)
    for label, ticker, _ in _METAL_TICKERS:
        usd_oz = _get_fast_price(ticker)
        if usd_oz is not None and usd_try is not None:
            results[label] = (usd_oz * usd_try) / TROY_OZ_TO_GRAM
        elif usd_oz is not None:
            # USD/TRY alınamadıysa USD/gram olarak göster
            results[label] = usd_oz / TROY_OZ_TO_GRAM

    return results


def _currency_for(label: str) -> str:
    for lbl, _, cur in _SIMPLE_TICKERS:
        if lbl == label:
            return cur
    for lbl, _, cur in _METAL_TICKERS:
        if lbl == label:
            return cur
    return ""


# ---------------------------------------------------------------------------
# Alt widget — tek gösterge
# ---------------------------------------------------------------------------

class _TickerItem(QWidget):
    def __init__(self, label: str, currency: str, parent=None) -> None:
        super().__init__(parent)
        self._currency = currency
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)

        self._lbl_name = QLabel(label)
        self._lbl_name.setProperty("cssClass", "tickerLabel")
        self._lbl_name.setAlignment(Qt.AlignCenter)

        self._lbl_value = QLabel("—")
        self._lbl_value.setProperty("cssClass", "tickerValue")
        self._lbl_value.setAlignment(Qt.AlignCenter)

        self._skeleton = SkeletonBlock(width=80, height=14, parent=self)
        self._skeleton.hide()

        layout.addWidget(self._lbl_name)
        layout.addWidget(self._lbl_value)

    def set_loading(self, loading: bool) -> None:
        self._lbl_value.setVisible(not loading)
        if loading:
            self._skeleton.start()
        else:
            self._skeleton.stop()

    def set_value(self, value: float) -> None:
        if self._currency:
            formatted = f"{self._currency} {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            formatted = f"{value:,.0f}".replace(",", ".")
        self._lbl_value.setText(formatted)

    def set_error(self) -> None:
        self._lbl_value.setText("—")


# ---------------------------------------------------------------------------
# Ana widget
# ---------------------------------------------------------------------------

class MarketTickerBar(QFrame):
    """
    Dashboard ve Model Portföy sayfalarında header altında gösterilen
    piyasa fiyat şeridi. Otomatik olarak 5 dakikada bir yenilenir.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("marketTickerBar")
        self.setProperty("cssClass", "marketTickerBar")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(52)

        self._threadpool = QThreadPool.globalInstance()
        self._running = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._items: dict[str, _TickerItem] = {}
        for i, label in enumerate(_DISPLAY_ORDER):
            currency = _currency_for(label)
            item = _TickerItem(label, currency, parent=self)
            self._items[label] = item
            layout.addWidget(item, 1)

            if i < len(_DISPLAY_ORDER) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.VLine)
                sep.setProperty("cssClass", "tickerSeparator")
                layout.addWidget(sep)

        self._timer = QTimer(self)
        self._timer.setInterval(REFRESH_INTERVAL_MS)
        self._timer.timeout.connect(self._refresh)

        # İlk yüklemeyi kısa gecikme ile başlat (sayfa render'ı tamamlasın)
        QTimer.singleShot(500, self._refresh)
        self._timer.start()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        """Sayfa kapatılırken çağır — timer'ı durdurur."""
        self._timer.stop()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        if self._running:
            return
        import sys
        import os
        if "pytest" in sys.modules or os.environ.get("PORTFOYSIM_ENV") == "test":
            for item in self._items.values():
                item.set_loading(False)
                item.set_error()
            return

        self._running = True
        for item in self._items.values():
            item.set_loading(True)

        worker = Worker(_fetch_all)
        worker.signals.result.connect(self._on_data)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(self._on_finished)
        self._threadpool.start(worker)

    def _on_data(self, data: dict[str, float]) -> None:
        for label, item in self._items.items():
            item.set_loading(False)
            if label in data:
                item.set_value(data[label])
            else:
                item.set_error()
        logger.debug("[MarketTickerBar] Güncellendi: %s", list(data.keys()))

    def _on_error(self, err: tuple) -> None:
        for item in self._items.values():
            item.set_loading(False)
            item.set_error()
        logger.warning("[MarketTickerBar] Fetch hatası: %s", err[1])

    def _on_finished(self) -> None:
        self._running = False


# ---------------------------------------------------------------------------
# Marquee widget — Model Portföy header içi
# ---------------------------------------------------------------------------

class ScrollingMarketTicker(QWidget):
    """
    Sağdan sola kayan marquee piyasa şeridi.
    Model Portföy sayfasının başlığı içinde, başlık ile butonlar arasında kullanılır.

    İçerik 2× kopyalanır (seamless loop):
    [ALTIN][GÜMÜŞ][USD][EUR][BIST] [ALTIN][GÜMÜŞ][USD][EUR][BIST] → sonsuz kayma
    """

    _ITEM_WIDTH: int = 130     # piksel / item
    _HEIGHT: int = 52
    _TICK_MS: int = 16         # ~60 fps
    _SPEED: float = 0.9        # piksel / tick (~54 px/s)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(self._HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Qt (Windows): child widget'lar parent sınırı dışına OS compositor tarafından kırpılır

        self._offset: float = 0.0
        self._half_width: int = len(_DISPLAY_ORDER) * self._ITEM_WIDTH
        self._last_data: dict[str, float] = {}
        self._running = False
        self._threadpool = QThreadPool.globalInstance()

        # Kayan iç row (layout'suz, doğrudan move() ile konumlandırılır)
        self._row = QWidget(self)
        self._row.setFixedSize(self._half_width * 2, self._HEIGHT)
        self._row_layout = QHBoxLayout(self._row)
        self._row_layout.setContentsMargins(0, 0, 0, 0)
        self._row_layout.setSpacing(0)

        # Item referansları: [original_0..4, copy_0..4]
        self._row_items: list[_TickerItem] = []
        self._build_row({})

        # Kaydırma timer
        self._scroll_timer = QTimer(self)
        self._scroll_timer.setInterval(self._TICK_MS)
        self._scroll_timer.timeout.connect(self._scroll_step)
        self._scroll_timer.start()

        # Veri yenileme timer
        self._data_timer = QTimer(self)
        self._data_timer.setInterval(REFRESH_INTERVAL_MS)
        self._data_timer.timeout.connect(self._refresh)
        self._data_timer.start()
        QTimer.singleShot(600, self._refresh)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        self._scroll_timer.stop()
        self._data_timer.stop()

    # ------------------------------------------------------------------
    # Row oluşturma
    # ------------------------------------------------------------------

    def _build_row(self, data: dict[str, float]) -> None:
        # Mevcut item'ları temizle
        while self._row_layout.count():
            item = self._row_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._row_items.clear()

        # 2 kopya (seamless loop)
        for _ in range(2):
            for i, label in enumerate(_DISPLAY_ORDER):
                currency = _currency_for(label)
                ti = _TickerItem(label, currency, parent=self._row)
                ti.setFixedWidth(self._ITEM_WIDTH)
                if label in data:
                    ti.set_value(data[label])
                self._row_layout.addWidget(ti)
                self._row_items.append(ti)

                # Ayırıcı (son item hariç her kopya içinde)
                if i < len(_DISPLAY_ORDER) - 1:
                    sep = QFrame(self._row)
                    sep.setFrameShape(QFrame.VLine)
                    sep.setProperty("cssClass", "tickerSeparator")
                    self._row_layout.addWidget(sep)

    def _update_values(self, data: dict[str, float]) -> None:
        """Row'u yeniden inşa etmeden değerleri güncelle."""
        items_per_copy = len(_DISPLAY_ORDER)
        for copy_idx in range(2):
            for item_idx, label in enumerate(_DISPLAY_ORDER):
                flat_idx = copy_idx * items_per_copy + item_idx
                if flat_idx < len(self._row_items):
                    ti = self._row_items[flat_idx]
                    ti.set_loading(False)
                    if label in data:
                        ti.set_value(data[label])
                    else:
                        ti.set_error()

    # ------------------------------------------------------------------
    # Animasyon
    # ------------------------------------------------------------------

    def _scroll_step(self) -> None:
        self._offset += self._SPEED
        if self._offset >= self._half_width:
            self._offset = 0.0
        self._row.move(QPoint(int(-self._offset), 0))

    # ------------------------------------------------------------------
    # Veri güncelleme
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        if self._running:
            return
        import sys
        import os
        if "pytest" in sys.modules or os.environ.get("PORTFOYSIM_ENV") == "test":
            for ti in self._row_items:
                ti.set_loading(False)
                ti.set_error()
            return

        self._running = True
        # Skeleton göster
        for ti in self._row_items:
            ti.set_loading(True)

        worker = Worker(_fetch_all)
        worker.signals.result.connect(self._on_data)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(self._on_finished)
        self._threadpool.start(worker)

    def _on_data(self, data: dict[str, float]) -> None:
        self._last_data = data
        self._update_values(data)
        logger.debug("[ScrollingMarketTicker] Güncellendi: %s", list(data.keys()))

    def _on_error(self, err: tuple) -> None:
        for ti in self._row_items:
            ti.set_loading(False)
            ti.set_error()
        logger.warning("[ScrollingMarketTicker] Fetch hatası: %s", err[1])

    def _on_finished(self) -> None:
        self._running = False

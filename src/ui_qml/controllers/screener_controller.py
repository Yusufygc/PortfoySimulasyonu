"""
ScreenerController — BIST Çoklu Sinyal Tarayıcısı QML controller'ı.

Sorumluluk:
- Hazır filtre listesini sağlama (SCREENER_FILTERS)
- Arka planda asenkron tarama başlatma
- Eşleşen hisseleri QML property'sine yansıtma
- Sonuç satırına tıklama → Hisse 360 yönlendirmesi
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.application.services.analysis.technical.screener import SCREENER_FILTERS

logger = logging.getLogger(__name__)


class ScreenerController(QObject):
    """QML context property: screenerController"""

    # --- Signals ---
    filterOptionsChanged = Signal()
    selectedFilterChanged = Signal()
    matchesChanged = Signal()
    isRunningChanged = Signal()
    statusTextChanged = Signal()
    operationResult = Signal(bool, str, arguments=["success", "message"])
    _scanCompleted = Signal(list)
    _scanFailed = Signal(str)

    def __init__(self, container, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._screener_service = getattr(container, "screener_service", None)
        self._executor = ThreadPoolExecutor(max_workers=1)

        # Thread-safe bağlantılar
        self._scanCompleted.connect(self._apply_results)
        self._scanFailed.connect(self._apply_error)

        # State
        self._filter_options: List[Dict[str, str]] = []
        self._selected_filter: str = ""  # "" = Tüm Stratejiler
        self._matches: List[Dict[str, Any]] = []
        self._is_running: bool = False
        self._status_text: str = "Taramaya hazır"

        self._build_filter_options()

    # ──────────────────────────── QML Properties ────────────────────────────

    @Property(list, notify=filterOptionsChanged)
    def filterOptions(self) -> list:
        return self._filter_options

    @Property(str, notify=selectedFilterChanged)
    def selectedFilter(self) -> str:
        return self._selected_filter

    @Property(list, notify=matchesChanged)
    def matchesList(self) -> list:
        return self._matches

    @Property(bool, notify=isRunningChanged)
    def isRunning(self) -> bool:
        return self._is_running

    @Property(str, notify=statusTextChanged)
    def statusText(self) -> str:
        return self._status_text

    # ──────────────────────────── QML Slots ────────────────────────────

    @Slot(str)
    def setFilter(self, filter_key: str) -> None:
        """Aktif filtreyi değiştirir (boş string = tüm stratejiler)."""
        self._selected_filter = filter_key
        self.selectedFilterChanged.emit()

    @Slot()
    def runScan(self) -> None:
        """Arka planda taramayı başlatır."""
        if self._screener_service is None:
            self._status_text = "Tarayıcı servisi bulunamadı"
            self.statusTextChanged.emit()
            return

        if self._is_running:
            return

        self._is_running = True
        self.isRunningChanged.emit()
        self._status_text = "Piyasa taranıyor, lütfen bekleyin..."
        self.statusTextChanged.emit()

        filter_keys = [self._selected_filter] if self._selected_filter else None
        future = self._executor.submit(self._screener_service.scan, filter_keys=filter_keys)
        future.add_done_callback(self._on_scan_complete)

    # ──────────────────────────── Internal ────────────────────────────

    def _build_filter_options(self) -> None:
        """Hazır filtre tanımlarından seçenek listesini oluşturur."""
        options = [{"key": "", "label": "Tüm Stratejiler"}]
        for key, fdef in SCREENER_FILTERS.items():
            options.append({"key": key, "label": fdef.label})
        self._filter_options = options
        self.filterOptionsChanged.emit()

    def _on_scan_complete(self, future) -> None:
        """Arka plan taraması tamamlandığında ana thread'e sonucu iletir."""
        try:
            results = future.result()
            self._scanCompleted.emit(results)
        except Exception as exc:
            logger.exception("Tarama hatası: %s", exc)
            self._scanFailed.emit(str(exc))

    def _apply_results(self, results) -> None:
        matches = []
        for m in results:
            matches.append({
                "ticker": m.ticker,
                "filterLabel": m.filter_label,
                "closePrice": f"{m.close_price:,.2f} ₺" if m.close_price else "-",
                "closePriceRaw": m.close_price or 0.0,
            })
        self._matches = matches
        self.matchesChanged.emit()
        if not matches:
            self._status_text = "Tarama tamamlandı: Kriterlere uyan hisse bulunamadı"
        else:
            self._status_text = f"Tarama tamamlandı: {len(matches)} hisse sinyal verdi"
        self.statusTextChanged.emit()
        self._is_running = False
        self.isRunningChanged.emit()

    def _apply_error(self, msg: str) -> None:
        self._status_text = f"Hata: {msg}"
        self.statusTextChanged.emit()
        self._is_running = False
        self.isRunningChanged.emit()

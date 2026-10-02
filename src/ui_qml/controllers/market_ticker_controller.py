"""
MarketTickerController — Üst piyasa şeridi (QML): ALTIN | GÜMÜŞ | USD/TRY | EUR/TRY | BIST 100.

Eski arayüzdeki `MarketTickerBar`ın karşılığıdır. Değerler arka plan thread'inde çekilir ve 5 dakikada bir yenilenir;
alınamayan gösterge atlanır, hiçbiri alınamazsa şerit gizlenir.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_MS = 5 * 60 * 1000
_STARTUP_DELAY_MS = 1500


def _fmt(value: float) -> str:
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def indicator_to_dict(indicator) -> Dict[str, Any]:
    change = indicator.change_pct
    value_text = _fmt(indicator.value) + (f" {indicator.currency}" if indicator.currency else "")
    return {
        "label": indicator.label,
        "valueText": value_text,
        "hasChange": change is not None,
        "changeText": "" if change is None else f"{change:+.2f}%".replace(".", ","),
        "isUp": change is not None and change >= 0,
    }


class MarketTickerController(QObject):
    """QML context property: marketTickerController"""

    itemsChanged = Signal()
    loadingChanged = Signal()

    _fetchFinished = Signal(object)

    def __init__(self, container=None, parent: QObject | None = None, autostart: bool = True) -> None:
        super().__init__(parent)
        self._container = container
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._items: List[Dict[str, Any]] = []
        self._loading = False
        self._fetchFinished.connect(self._on_fetch_finished)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        if self._service is not None and autostart:
            self._timer.start(REFRESH_INTERVAL_MS)
            QTimer.singleShot(_STARTUP_DELAY_MS, self.refresh)

    @property
    def _service(self):
        return getattr(self._container, "market_indicators_service", None) if self._container else None

    @Property("QVariantList", notify=itemsChanged)
    def items(self) -> list:
        return self._items

    @Property(bool, notify=loadingChanged)
    def isLoading(self) -> bool:
        return self._loading

    @Slot()
    def refresh(self) -> None:
        service = self._service
        if service is None or self._loading:
            return
        self._loading = True
        self.loadingChanged.emit()

        def work() -> None:
            try:
                self._fetchFinished.emit(service.get_indicators())
            except Exception as exc:
                logger.debug("Piyasa şeridi yenilenemedi: %s", exc)
                self._fetchFinished.emit(None)

        self._executor.submit(work)

    def _on_fetch_finished(self, indicators) -> None:
        self._loading = False
        self.loadingChanged.emit()
        if indicators:  # hata/boş sonuçta son başarılı değerler gösterilmeye devam eder
            self._items = [indicator_to_dict(i) for i in indicators]
            self.itemsChanged.emit()

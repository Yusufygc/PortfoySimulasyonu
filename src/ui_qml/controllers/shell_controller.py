"""
Shell Controller — QML ana pencere, navigasyon ve piyasa seans durumunu yönetir.
"""
from __future__ import annotations

import datetime
import logging
from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer
from src.ui.shared.locale_tr import L10N

logger = logging.getLogger(__name__)


class ShellController(QObject):
    activePageChanged = Signal(int)
    pageTitleChanged = Signal(str)
    marketStatusChanged = Signal()
    timeTick = Signal(str)

    PAGE_TITLES = {
        0: L10N.DASHBOARD,
        1: L10N.LISTELERIM,
        2: L10N.MODEL_PORTFOYLER,
        3: L10N.NAV_STOCK_360,
        4: L10N.KARSILASTIRMA_LABORATUVARI,
        5: L10N.NAV_SCREENER,
        6: L10N.FINANSAL_PLANLAMA,
        7: L10N.OPTIMIZASYON,
        8: L10N.AI_ASISTAN,
        9: L10N.SETTINGS,
    }

    def __init__(self, container=None, parent=None):
        super().__init__(parent)
        self._container = container
        self._active_page: int = 0
        self._is_maximized: bool = False
        self._bist_open: bool = False
        self._session_text: str = "Piyasa Kapalı"
        self._current_time_str: str = ""

        # Clock & Session Timer
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._on_clock_tick)
        self._clock_timer.start()

        self._on_clock_tick()

    def _on_clock_tick(self) -> None:
        now = datetime.datetime.now()
        self._current_time_str = now.strftime("%H:%M:%S")
        self.timeTick.emit(self._current_time_str)

        was_open = self._bist_open
        self._bist_open = self._is_session_open(now)
        self._session_text = "BIST: Canlı Seans Açık" if self._bist_open else "BIST: Seans Kapalı"

        if was_open != self._bist_open:
            self.marketStatusChanged.emit()

    def _is_session_open(self, now: datetime.datetime) -> bool:
        """Seans durumunu tatil/yarım gün takvimini bilen servisten okur; servis yoksa hafta içi 10:00-18:10."""
        session_service = getattr(self._container, "bist_market_session_service", None) if self._container else None
        if session_service is not None:
            try:
                return bool(session_service.status_for(now.date(), now.time()).is_open)
            except Exception:
                logger.debug("Seans servisi okunamadı, varsayılan takvim kullanılıyor.", exc_info=True)
        minutes = now.hour * 60 + now.minute
        return now.weekday() < 5 and 600 <= minutes <= 1090

    # --- Properties ---

    @Property(int, notify=activePageChanged)
    def activePage(self) -> int:
        return self._active_page

    @Property(str, notify=pageTitleChanged)
    def pageTitle(self) -> str:
        return self.PAGE_TITLES.get(self._active_page, "Portföy Simülasyonu")

    @Property(bool, notify=marketStatusChanged)
    def isBistOpen(self) -> bool:
        return self._bist_open

    @Property(str, notify=marketStatusChanged)
    def sessionText(self) -> str:
        return self._session_text

    @Property(str, notify=timeTick)
    def currentTime(self) -> str:
        return self._current_time_str

    # --- Slots ---

    @Slot(int)
    def navigateTo(self, page_index: int) -> None:
        if self._active_page != page_index and page_index in self.PAGE_TITLES:
            self._active_page = page_index
            self.activePageChanged.emit(self._active_page)
            self.pageTitleChanged.emit(self.pageTitle)

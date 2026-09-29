"""
Shell Controller — QML ana pencere, navigasyon ve piyasa seans durumunu yönetir.
"""
from __future__ import annotations

import datetime
from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer
from src.ui.shared.locale_tr import L10N


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

        # Check BIST Session (Hafta içi 10:00 - 18:00)
        is_weekday = now.weekday() < 5
        hour = now.hour
        minute = now.minute
        time_minutes = hour * 60 + minute

        # 10:00 = 600, 18:05 = 1085
        was_open = self._bist_open
        if is_weekday and (600 <= time_minutes <= 1085):
            self._bist_open = True
            self._session_text = "BIST: Canlı Seans Açık"
        else:
            self._bist_open = False
            self._session_text = "BIST: Seans Kapalı"

        if was_open != self._bist_open:
            self.marketStatusChanged.emit()

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

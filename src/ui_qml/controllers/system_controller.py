"""
SystemController — Ayarlar > Sistem sekmesi (QML).

Eski arayüzdeki `ResetPanel`ın karşılığıdır:
1. Otomatik canlı fiyat yenileme (aç/kapa + 5/15/30/60 dk aralık). Aynı QSettings anahtarlarını kullanır.
   Zamanlayıcı seçili aralıkta `LivePriceRefreshService.refresh_active_prices` çalıştırır (yalnızca seans açıkken).
2. Sistemi sıfırlama (`PortfolioResetService.reset_all`): tüm portföy, fiyat ve hisse verisini siler.
Ağır işler arka plan thread'inde çalışır, sonuçlar Qt sinyalleriyle ana thread'e taşınır.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from typing import Any, Optional

from PySide6.QtCore import Property, QObject, QSettings, QTimer, Signal, Slot

logger = logging.getLogger(__name__)

LIVE_PRICE_REFRESH_ENABLED_KEY = "settings/live_price_refresh_enabled"
LIVE_PRICE_REFRESH_INTERVAL_KEY = "settings/live_price_refresh_interval_minutes"
LAST_LIVE_PRICE_REFRESH_KEY = "settings/last_live_price_refresh_at"
DEFAULT_ENABLED = True
DEFAULT_INTERVAL_MINUTES = 15
INTERVAL_OPTIONS = (5, 15, 30, 60)
_STARTUP_DELAY_MS = 6000
_ERROR_TOAST_THRESHOLD = 3


def _to_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "hayir", "hayır", "no", "off"}
    return bool(value)


class SystemController(QObject):
    """QML context property: systemController"""

    liveRefreshChanged = Signal()
    busyChanged = Signal()
    # (success, message) — Ayarlar toast'ı
    notification = Signal(bool, str, arguments=["success", "message"])
    # Canlı fiyatlar yazıldı: Dashboard/Model/İzleme ekranları yeniden okunmalı
    pricesRefreshed = Signal()
    # Sistem sıfırlandı: tüm veri ekranları yeniden okunmalı
    systemReset = Signal()

    _refreshFinished = Signal(object, str)
    _resetFinished = Signal(bool, str)

    def __init__(
        self,
        container=None,
        parent: QObject | None = None,
        settings: QSettings | None = None,
        autostart: bool = True,
    ) -> None:
        super().__init__(parent)
        self._container = container
        self._settings = settings or QSettings("PortfoySimulasyonu", "PortfoySimulasyonu")
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._is_refreshing = False
        self._is_resetting = False
        self._consecutive_errors = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refreshNow)
        self._refreshFinished.connect(self._on_refresh_finished)
        self._resetFinished.connect(self._on_reset_finished)
        self._apply_timer()
        if autostart:
            QTimer.singleShot(_STARTUP_DELAY_MS, self.refreshNow)

    def _svc(self, name: str):
        return getattr(self._container, name, None) if self._container else None

    # ------------------------------------------------------------------ properties

    @Property(bool, notify=liveRefreshChanged)
    def liveRefreshEnabled(self) -> bool:
        return _to_bool(self._settings.value(LIVE_PRICE_REFRESH_ENABLED_KEY, DEFAULT_ENABLED), DEFAULT_ENABLED)

    @Property(int, notify=liveRefreshChanged)
    def liveRefreshInterval(self) -> int:
        try:
            minutes = int(self._settings.value(LIVE_PRICE_REFRESH_INTERVAL_KEY, DEFAULT_INTERVAL_MINUTES))
        except (TypeError, ValueError):
            minutes = DEFAULT_INTERVAL_MINUTES
        return minutes if minutes in INTERVAL_OPTIONS else DEFAULT_INTERVAL_MINUTES

    @Property("QVariantList", constant=True)
    def intervalOptions(self) -> list:
        return [{"minutes": m, "label": f"{m} dk"} for m in INTERVAL_OPTIONS]

    @Property(str, notify=liveRefreshChanged)
    def lastRefreshText(self) -> str:
        raw = self._settings.value(LAST_LIVE_PRICE_REFRESH_KEY, "", type=str)
        try:
            return datetime.fromisoformat(raw).strftime("%d.%m.%Y %H:%M") if raw else ""
        except ValueError:
            return ""

    @Property(bool, notify=busyChanged)
    def isResetting(self) -> bool:
        return self._is_resetting

    @Property(bool, notify=busyChanged)
    def isRefreshing(self) -> bool:
        return self._is_refreshing

    @Property(bool, constant=True)
    def resetAvailable(self) -> bool:
        return self._svc("reset_service") is not None

    # ------------------------------------------------------------------ canlı fiyat yenileme

    @Slot(bool)
    def setLiveRefreshEnabled(self, enabled: bool) -> None:
        self._settings.setValue(LIVE_PRICE_REFRESH_ENABLED_KEY, bool(enabled))
        self._settings.sync()
        self._apply_timer()
        self.liveRefreshChanged.emit()
        if enabled:
            self.refreshNow()

    @Slot(int)
    def setLiveRefreshInterval(self, minutes: int) -> None:
        if minutes not in INTERVAL_OPTIONS:
            return
        self._settings.setValue(LIVE_PRICE_REFRESH_INTERVAL_KEY, int(minutes))
        self._settings.sync()
        self._apply_timer()
        self.liveRefreshChanged.emit()

    def _apply_timer(self) -> None:
        self._timer.stop()
        if self.liveRefreshEnabled:
            self._timer.start(self.liveRefreshInterval * 60_000)

    def _session_open(self) -> bool:
        session = self._svc("bist_market_session_service")
        if session is None:
            return True
        try:
            return bool(session.status_for(date.today()).is_open)
        except Exception as exc:
            logger.warning("BIST seans kontrolü başarısız: %s", exc)
            return True

    @Slot()
    def refreshNow(self) -> None:
        """Seans açıksa aktif pozisyonların canlı fiyatlarını yeniler (zamanlayıcı ve elle çağrı)."""
        service = self._svc("live_price_refresh_service")
        if service is None or self._is_refreshing or not self.liveRefreshEnabled or not self._session_open():
            return
        self._is_refreshing = True
        self.busyChanged.emit()

        def work() -> None:
            try:
                self._refreshFinished.emit(service.refresh_active_prices(), "")
            except Exception as exc:
                logger.warning("Otomatik fiyat yenileme başarısız: %s", exc)
                self._refreshFinished.emit(None, str(exc))

        self._executor.submit(work)

    def _on_refresh_finished(self, result: Any, error: str) -> None:
        self._is_refreshing = False
        self.busyChanged.emit()
        if error:
            self._consecutive_errors += 1
            if self._consecutive_errors >= _ERROR_TOAST_THRESHOLD:
                self._consecutive_errors = 0
                self.notification.emit(False, f"Otomatik fiyat yenileme çalıştırılamadı: {error}")
            return
        self._consecutive_errors = 0
        prices = getattr(result, "prices", None)
        event_bus = self._svc("event_bus")
        if prices and event_bus is not None:
            event_bus.prices_updated.emit(dict(prices))
        finished = getattr(result, "finished_at", None)
        stamp = finished if isinstance(finished, datetime) else datetime.now()
        self._settings.setValue(LAST_LIVE_PRICE_REFRESH_KEY, stamp.replace(tzinfo=None).isoformat(timespec="seconds"))
        self._settings.sync()
        self.liveRefreshChanged.emit()
        if getattr(result, "updated_count", 0) > 0:
            self.pricesRefreshed.emit()

    # ------------------------------------------------------------------ sistemi sıfırlama

    @Slot()
    def resetAll(self) -> None:
        """Onay QML diyaloğunda alınır; tüm portföy/fiyat/hisse verisini siler."""
        service = self._svc("reset_service")
        if service is None:
            self.notification.emit(False, "Sıfırlama servisi bulunamadı.")
            return
        if self._is_resetting:
            return
        self._is_resetting = True
        self.busyChanged.emit()

        def work() -> None:
            try:
                service.reset_all()
                self._resetFinished.emit(True, "")
            except Exception as exc:
                logger.exception("Sistem sıfırlanamadı: %s", exc)
                self._resetFinished.emit(False, str(exc))

        self._executor.submit(work)

    def _on_reset_finished(self, success: bool, error: str) -> None:
        self._is_resetting = False
        self.busyChanged.emit()
        if success:
            self.notification.emit(True, "Sistem başarıyla sıfırlandı.")
            self.systemReset.emit()
        else:
            self.notification.emit(False, f"Sistem sıfırlanamadı: {error}")

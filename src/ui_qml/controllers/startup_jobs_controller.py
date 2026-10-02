"""
StartupJobsController — Uygulama açılışında çalışan otomatik veri bakım işleri (QML).

Eski arayüzdeki `MainWindow` açılış işlerinin karşılığıdır; aynı QSettings anahtarlarını kullanır,
böylece iki arayüz aynı günde işi iki kez çalıştırmaz:
1. Portföy hisseleri için son güncel günden bugüne eksik kapanışları tamamlama
2. Tüm BIST hisseleri için eksik kapanışları tamamlama (seans kapanışı sonrası, 18:30'dan itibaren)
3. KAP/MKK kurumsal aksiyon adaylarını günde bir kez tarama
4. Golden/Death Cross teknik taramasını son taramadan 24 saat geçmişse çalıştırma

İşler tek bir arka plan thread'inde sırayla çalışır (veri kaynağını aynı anda yormamak için).
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time as dt_time, timedelta
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, QSettings, QTimer, Signal

logger = logging.getLogger(__name__)

AUTO_BACKFILL_SETTINGS_KEY = "settings/last_auto_price_backfill_at"
AUTO_BIST_BACKFILL_SETTINGS_KEY = "settings/last_auto_bist_backfill_at"
AUTO_CORPORATE_ACTION_DISCOVERY_SETTINGS_KEY = "settings/last_auto_corporate_action_discovery_at"
AUTO_TECHNICAL_SCAN_SETTINGS_KEY = "settings/last_auto_technical_scan_at"
TECHNICAL_SCAN_INTERVAL = timedelta(hours=24)
BIST_MARKET_CLOSE_TIME = dt_time(18, 30)
STARTUP_DELAY_MS = 8000


def last_completed_trading_day(today: date, trading_calendar) -> date:
    candidate = today - timedelta(days=1)
    while trading_calendar is not None and not trading_calendar.is_trading_day(candidate):
        candidate -= timedelta(days=1)
    return candidate


class StartupJobsController(QObject):
    """QML context property: startupJobsController"""

    # (success, message) — Main.qml global toast'ı
    jobNotification = Signal(bool, str, arguments=["success", "message"])
    # Yeni fiyat yazıldı; Dashboard/Model ekranları yenilenmeli
    pricesUpdated = Signal()

    _jobDone = Signal(str, object, str)

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
        self._jobDone.connect(self._on_job_done)
        self._targets: dict[str, Any] = {}
        if autostart:
            QTimer.singleShot(STARTUP_DELAY_MS, self.runAll)

    def _svc(self, name: str):
        return getattr(self._container, name, None) if self._container else None

    def runAll(self) -> None:
        """Gün içinde zaten çalışmış işleri atlayarak tüm açılış işlerini kuyruğa alır."""
        self._queue_price_backfill()
        self._queue_bist_backfill()
        self._queue_corporate_action_discovery()
        self._queue_technical_scan()

    # ------------------------------------------------------------------ iş kuyruğa alma

    def _submit(self, job: str, fn: Callable, *args) -> None:
        def work() -> None:
            try:
                self._jobDone.emit(job, fn(*args), "")
            except Exception as exc:
                logger.warning("Açılış işi başarısız (%s): %s", job, exc, exc_info=True)
                self._jobDone.emit(job, None, str(exc))

        self._executor.submit(work)

    def _queue_price_backfill(self) -> None:
        service = self._svc("price_data_health_service")
        if service is None:
            return
        target = last_completed_trading_day(date.today(), self._svc("trading_calendar"))
        if self._settings.value(AUTO_BACKFILL_SETTINGS_KEY, "", type=str) == target.isoformat():
            return
        self._targets["price_backfill"] = target
        self._submit("price_backfill", service.update_from_latest_to_today, target)

    def _queue_bist_backfill(self) -> None:
        """Tüm BIST için eksik kapanışları DuckDB piyasa geçmişine artımlı senkronla tamamlar."""
        service = self._svc("market_data_sync_service")
        if service is None:
            return
        if datetime.now().time() < BIST_MARKET_CLOSE_TIME:
            logger.info("BIST backfill atlandı (saat < 18:30, piyasa açık olabilir)")
            return
        target = last_completed_trading_day(date.today(), self._svc("trading_calendar"))
        if self._settings.value(AUTO_BIST_BACKFILL_SETTINGS_KEY, "", type=str) == target.isoformat():
            return
        self._targets["bist_backfill"] = target
        self._submit("bist_backfill", service.sync_daily_delta)

    def _queue_corporate_action_discovery(self) -> None:
        service = self._svc("corporate_action_discovery_service")
        if service is None:
            return
        if self._settings.value(AUTO_CORPORATE_ACTION_DISCOVERY_SETTINGS_KEY, "", type=str) == date.today().isoformat():
            return
        self._submit("corporate_action_discovery", service.discover)

    def _queue_technical_scan(self) -> None:
        service = self._svc("technical_analysis_service")
        if service is None:
            return
        last_scan = self._settings.value(AUTO_TECHNICAL_SCAN_SETTINGS_KEY, "", type=str)
        if last_scan:
            try:
                if datetime.now() - datetime.fromisoformat(last_scan) <= TECHNICAL_SCAN_INTERVAL:
                    return
            except ValueError:
                pass  # bozuk kayıt: taramayı çalıştır
        self._submit("technical_scan", service.scan_all)

    # ------------------------------------------------------------------ sonuç işleme (ana thread)

    def _remember(self, key: str, value: str) -> None:
        self._settings.setValue(key, value)
        self._settings.sync()

    def _on_job_done(self, job: str, result: Any, error: str) -> None:
        if error:
            messages = {
                "price_backfill": "Otomatik veri güncelleme çalıştırılamadı",
                "bist_backfill": "Otomatik BIST güncellemesi çalıştırılamadı",
                "corporate_action_discovery": "Kurumsal aksiyon taraması çalıştırılamadı",
                "technical_scan": "Otomatik Golden Cross taraması çalıştırılamadı",
            }
            logger.warning("%s: %s", messages.get(job, job), error)
            self.jobNotification.emit(False, f"{messages.get(job, job)}: {error}")
            return
        if job == "price_backfill":
            self._finish_backfill(result, AUTO_BACKFILL_SETTINGS_KEY, "price_backfill", "Otomatik veri güncelleme")
        elif job == "bist_backfill":
            self._finish_bist_sync(result)
        elif job == "corporate_action_discovery":
            self._remember(AUTO_CORPORATE_ACTION_DISCOVERY_SETTINGS_KEY, date.today().isoformat())
            saved = getattr(result, "saved_count", 0)
            if saved > 0:
                self.jobNotification.emit(True, f"{saved} yeni kurumsal aksiyon adayı bulundu. Ayarlar > Kurumsal Aksiyonlar'dan inceleyin.")
        elif job == "technical_scan":
            self._remember(AUTO_TECHNICAL_SCAN_SETTINGS_KEY, datetime.now().isoformat())
            new_events = getattr(result, "new_event_count", 0)
            if new_events > 0:
                self.jobNotification.emit(True, f"Golden Cross taraması tamamlandı: {new_events} yeni sinyal.")

    def _finish_bist_sync(self, result: Any) -> None:
        target = self._targets.get("bist_backfill") or last_completed_trading_day(date.today(), self._svc("trading_calendar"))
        errors = len(getattr(result, "errors", []) or [])
        if not errors:
            self._remember(AUTO_BIST_BACKFILL_SETTINGS_KEY, target.isoformat())
        added = getattr(result, "added_bars", 0)
        if added > 0:
            self.pricesUpdated.emit()
            self.jobNotification.emit(True, f"Otomatik BIST güncellemesi tamamlandı: {added} fiyat kaydı eklendi.")
        elif errors:
            self.jobNotification.emit(False, f"Otomatik BIST güncellemesi sırasında {errors} hata oluştu.")

    def _finish_backfill(self, result: Any, key: str, target_key: str, label: str) -> None:
        target = self._targets.get(target_key) or last_completed_trading_day(date.today(), self._svc("trading_calendar"))
        self._remember(key, target.isoformat())
        prices = getattr(result, "prices", None)
        event_bus = self._svc("event_bus")
        if prices and event_bus is not None:
            event_bus.prices_updated.emit(dict(prices))
        updated = getattr(result, "updated_count", 0)
        errors = len(getattr(result, "errors", []) or [])
        if updated > 0:
            self.pricesUpdated.emit()
            self.jobNotification.emit(True, f"{label} tamamlandı: {updated} fiyat kaydı eklendi.")
        elif errors:
            self.jobNotification.emit(False, f"{label} sırasında {errors} hata oluştu.")

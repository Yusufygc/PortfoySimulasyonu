"""
StartupJobsController — Uygulama açılışında çalışan otomatik veri bakım işleri (QML).

Eski arayüzdeki `MainWindow` açılış işlerinin karşılığıdır; aynı QSettings anahtarlarını kullanır,
böylece iki arayüz aynı günde işi iki kez çalıştırmaz:
1. Portföy hisseleri için son güncel günden kapanış verisi hazır son işlem gününe kadar eksik kapanışları tamamlama
   (BIST dışı hisseler için tek yol; BIST tamamı `MarketSyncController` artımlı senkronuyla gelir)
2. KAP/MKK kurumsal aksiyon adaylarını günde bir kez tarama
3. Golden/Death Cross teknik taramasını son taramadan 24 saat geçmişse çalıştırma
4. Hisse bölünmelerini günde bir kez tarayıp iki kaynağın doğruladıklarını otomatik uygulama (`SplitAutomationService`)

İşler tek bir arka plan thread'inde sırayla çalışır (veri kaynağını aynı anda yormamak için). Uygulamada açılıştaki ilk
kapanış senkronu bittikten sonra başlar (`start_after`); böylece aynı kapanışlar iki yoldan indirilmez.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, QSettings, Signal
from src.application.services.market.bist_market_session_service import BistMarketSessionService
from src.domain.market_clock import market_now, market_today
from src.ui_qml.messages import msg
from src.qt_compat.user_settings import user_settings
from src.ui_qml.deferred import run_later

logger = logging.getLogger(__name__)

AUTO_BACKFILL_SETTINGS_KEY = "settings/last_auto_price_backfill_at"
AUTO_CORPORATE_ACTION_DISCOVERY_SETTINGS_KEY = "settings/last_auto_corporate_action_discovery_at"
AUTO_TECHNICAL_SCAN_SETTINGS_KEY = "settings/last_auto_technical_scan_at"
AUTO_SPLIT_SCAN_SETTINGS_KEY = "settings/last_auto_split_scan_at"
TECHNICAL_SCAN_INTERVAL = timedelta(hours=24)
STARTUP_DELAY_MS = 8000
# `start_after` sinyali (ilk kapanış senkronunun bitişi) hiç gelmezse açılış işleri bu süre sonunda yine başlar
STARTUP_FALLBACK_MS = 120_000


def last_completed_trading_day(now: datetime, trading_calendar) -> date:
    """Kapanış verisi hazır olan son işlem günü (tek kaynak: `BistMarketSessionService`, 18:30'dan sonra bugün)."""
    return BistMarketSessionService(trading_calendar).last_completed_trading_day(now)


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
        self._settings = settings or user_settings()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._jobDone.connect(self._on_job_done)
        self._targets: dict[str, Any] = {}
        self._started = False
        if autostart:
            run_later(self, STARTUP_DELAY_MS, self._start_once)

    def _svc(self, name: str):
        return getattr(self._container, name, None) if self._container else None

    def start_after(self, signal) -> None:
        """Açılış işlerini verilen sinyalden (ilk kapanış senkronunun bitişi) sonra bir kez başlatır.

        Senkron, BIST portföy hisselerinin kapanışlarını SQLite'a zaten yazar; tamamlama ondan önce başlarsa aynı hisseleri
        tek tek yeniden indirir ve aynı satırları eşzamanlı yazardı. Sinyal gelmezse yedek süre sonunda başlar.
        """
        signal.connect(self._start_once)
        run_later(self, STARTUP_FALLBACK_MS, self._start_once)

    def _start_once(self) -> None:
        if self._started:
            return
        self._started = True
        self.runAll()

    def runAll(self) -> None:
        """Gün içinde zaten çalışmış işleri atlayarak tüm açılış işlerini kuyruğa alır."""
        self._queue_price_backfill()
        self._queue_corporate_action_discovery()
        self._queue_split_automation()
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
        target = last_completed_trading_day(market_now(), self._svc("trading_calendar"))
        if self._settings.value(AUTO_BACKFILL_SETTINGS_KEY, "", type=str) == target.isoformat():
            return
        self._targets["price_backfill"] = target
        self._submit("price_backfill", service.update_from_latest_to_today, target)

    def _queue_corporate_action_discovery(self) -> None:
        service = self._svc("corporate_action_discovery_service")
        if service is None:
            return
        if self._settings.value(AUTO_CORPORATE_ACTION_DISCOVERY_SETTINGS_KEY, "", type=str) == market_today().isoformat():
            return
        self._submit("corporate_action_discovery", service.discover)

    def _queue_split_automation(self) -> None:
        service = self._svc("split_automation_service")
        if service is None:
            return
        if self._settings.value(AUTO_SPLIT_SCAN_SETTINGS_KEY, "", type=str) == market_today().isoformat():
            return
        self._submit("split_automation", service.run)

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
                "price_backfill": msg("startup.otomatik_veri_guncelleme_calistirilamadi"),
                "corporate_action_discovery": msg("startup.kurumsal_aksiyon_taramasi_calistirilamadi"),
                "technical_scan": msg("startup.otomatik_golden_cross_taramasi_calistirilama"),
                "split_automation": msg("startup.bolunme_taramasi_calistirilamadi"),
            }
            logger.warning("%s: %s", messages.get(job, job), error)
            self.jobNotification.emit(False, f"{messages.get(job, job)}: {error}")
            return
        if job == "price_backfill":
            self._finish_backfill(result, AUTO_BACKFILL_SETTINGS_KEY, "price_backfill", msg("startup.otomatik_veri_guncelleme"))
        elif job == "corporate_action_discovery":
            self._remember(AUTO_CORPORATE_ACTION_DISCOVERY_SETTINGS_KEY, market_today().isoformat())
            saved = getattr(result, "saved_count", 0)
            if saved > 0:
                self.jobNotification.emit(True, msg("startup.yeni_kurumsal_aksiyon_adayi_bulundu_ayarlar", saved=saved))
        elif job == "split_automation":
            self._finish_split_automation(result)
        elif job == "technical_scan":
            self._remember(AUTO_TECHNICAL_SCAN_SETTINGS_KEY, datetime.now().isoformat())
            new_events = getattr(result, "new_event_count", 0)
            if new_events > 0:
                self.jobNotification.emit(True, msg("startup.golden_cross_taramasi_tamamlandi_yeni_sinyal", new_events=new_events))

    def _finish_split_automation(self, result: Any) -> None:
        self._remember(AUTO_SPLIT_SCAN_SETTINGS_KEY, market_today().isoformat())
        applied = getattr(result, "applied", []) or []
        candidates = getattr(result, "candidates", []) or []
        if applied:
            self.jobNotification.emit(True, msg("startup.bolunme_otomatik_uygulandi", summary=result.summary))
            self.pricesUpdated.emit()  # işlemler ve fiyat geçmişi değişti: ekranlar yenilensin
        if candidates:
            self.jobNotification.emit(True, msg("startup.bolunme_adayi_onay_bekliyor", count=len(candidates)))

    def _finish_backfill(self, result: Any, key: str, target_key: str, label: str) -> None:
        target = self._targets.get(target_key) or last_completed_trading_day(market_now(), self._svc("trading_calendar"))
        self._remember(key, target.isoformat())
        prices = getattr(result, "prices", None)
        event_bus = self._svc("event_bus")
        if prices and event_bus is not None:
            event_bus.prices_updated.emit(dict(prices))
        updated = getattr(result, "updated_count", 0)
        errors = len(getattr(result, "errors", []) or [])
        if updated > 0:
            self.pricesUpdated.emit()
            self.jobNotification.emit(True, msg("startup.tamamlandi_fiyat_kaydi_eklendi", label=label, updated=updated))
        elif errors:
            self.jobNotification.emit(False, msg("startup.sirasinda_hata_olustu", label=label, errors=errors))

"""
MarketSyncController — Piyasa verisi senkronizasyonunun QML controller'ı ve arka plan nöbetçisi.

Sorumluluklar:
1. Uygulama Açılışı (Startup Catch-up): Açılıştan 5 saniye sonra eksik gün farkını sessizce kapatır.
2. Seans Kapanış Nöbetçisi (Market Close Watcher): Hafta içi saat 18:15 olduğunda otomatik tetiklenir.
3. Manuel Tetikleme: Kullanıcı veya buton istediğinde anında senkronizasyon başlatabilir.
4. UI Bildirimi: Başarı ve durum değişikliklerini QML ToastNotification bileşenine aktarır.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time as dt_time
from typing import Optional

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from src.application.services.market_data.market_data_sync_service import (
    MarketDataSyncService,
    MarketSyncResult,
)

logger = logging.getLogger(__name__)

_MARKET_CLOSE_TIME = dt_time(18, 15)


class MarketSyncController(QObject):
    """QML context property: marketSyncController"""

    isSyncingChanged = Signal()
    statusTextChanged = Signal()
    lastSyncTimeChanged = Signal()
    isUpToDateChanged = Signal()
    syncNotification = Signal(bool, str, arguments=["success", "message"])
    # Yeni bar yazıldığında yayınlanır; fiyatlara bağlı ekranlar (Dashboard, Model Portföy) yenilenir.
    dataSynced = Signal()

    # Worker thread sinyalleri (Thread-safe)
    _syncWorkerFinished = Signal(object)
    _syncWorkerFailed = Signal(str)

    def __init__(
        self,
        sync_service: Optional[MarketDataSyncService] = None,
        parent: QObject | None = None,
        container=None,
    ) -> None:
        super().__init__(parent)
        self._sync_service = sync_service or self._build_sync_service(container)
        self._executor = ThreadPoolExecutor(max_workers=1)

        # Thread-safe bağlantılar
        self._syncWorkerFinished.connect(self._on_sync_finished)
        self._syncWorkerFailed.connect(self._on_sync_failed)

        # State
        self._is_syncing: bool = False
        self._status_text: str = "Piyasa verisi hazır"
        self._last_sync_time: str = "-"
        self._is_up_to_date: bool = True
        self._last_auto_synced_date: Optional[date] = None

        # 1. Başlangıç gecikmeli kontrolü (5 sn sonra)
        QTimer.singleShot(5000, self._startup_check_and_sync)

        # 2. Periyodik nöbetçi timer (Her 60 saniyede bir)
        self._watcher_timer = QTimer(self)
        self._watcher_timer.setInterval(60_000)  # 60 saniye
        self._watcher_timer.timeout.connect(self._on_watcher_tick)
        self._watcher_timer.start()

    @staticmethod
    def _build_sync_service(container) -> MarketDataSyncService:
        """Container'ın senkron servisini (SQLite köprüsü + tatil takvimi bağlı) kullanır; yoksa varsayılanı kurar."""
        service = getattr(container, "market_data_sync_service", None) if container else None
        return service if isinstance(service, MarketDataSyncService) else MarketDataSyncService()

    # ──────────────────────────── QML Properties ────────────────────────────

    @Property(bool, notify=isSyncingChanged)
    def isSyncing(self) -> bool:
        return self._is_syncing

    @Property(str, notify=statusTextChanged)
    def statusText(self) -> str:
        return self._status_text

    @Property(bool, notify=isUpToDateChanged)
    def isUpToDate(self) -> bool:
        return self._is_up_to_date

    # ──────────────────────────── QML Slots ────────────────────────────

    @Slot()
    def triggerSyncNow(self) -> None:
        """Kullanıcı veya sistem tarafından anında artımlı senkronizasyon başlatır."""
        if self._is_syncing:
            return

        self._is_syncing = True
        self.isSyncingChanged.emit()
        self._status_text = "Borsa kapanış verileri senkronize ediliyor..."
        self.statusTextChanged.emit()

        future = self._executor.submit(self._sync_service.sync_daily_delta)
        future.add_done_callback(self._on_future_done)

    # ──────────────────────────── Internal Nöbetçi Mantığı ────────────────────────────

    def _startup_check_and_sync(self) -> None:
        """Uygulama açıldıktan sonra eksik gün kontrolü yapar."""
        try:
            status = self._sync_service.get_sync_status()
            self._is_up_to_date = status.is_up_to_date
            self.isUpToDateChanged.emit()
            # Güncel olsa bile çalışır: DuckDB'de olup SQLite'a yazılamamış barlar uzlaştırılır
            logger.info("Uygulama başlangıcı: %s -> Senkronizasyon/uzlaştırma başlatılıyor.", status.message)
            self.triggerSyncNow()
        except Exception as exc:
            logger.warning("Startup sync kontrolü hatası: %s", exc)

    def _on_watcher_tick(self) -> None:
        """Her 60 saniyede bir seans kapanış saatini kontrol eder."""
        now = datetime.now()
        current_date = now.date()
        current_time = now.time()

        # Hafta içi mi ve 18:15'i geçti mi?
        if now.weekday() < 5 and current_time >= _MARKET_CLOSE_TIME:
            # Bugün için otomatik güncelleme daha önce yapılmadıysa
            if self._last_auto_synced_date != current_date and not self._is_syncing:
                logger.info("Seans kapandı (18:15 geçti) -> Gün sonu kapanış verileri otomatik güncelleniyor.")
                self._last_auto_synced_date = current_date
                self.triggerSyncNow()

    def _on_future_done(self, future) -> None:
        try:
            res = future.result()
            self._syncWorkerFinished.emit(res)
        except Exception as exc:
            logger.exception("Arka plan senkronizasyon hatası: %s", exc)
            self._syncWorkerFailed.emit(str(exc))

    def _on_sync_finished(self, result: MarketSyncResult) -> None:
        self._is_syncing = False
        self.isSyncingChanged.emit()

        now_str = datetime.now().strftime("%H:%M:%S")
        self._last_sync_time = now_str
        self.lastSyncTimeChanged.emit()

        self._is_up_to_date = result.is_up_to_date
        self.isUpToDateChanged.emit()

        self._status_text = result.message
        self.statusTextChanged.emit()

        if result.added_bars > 0:
            msg = f"Borsa verileri güncellendi: {result.updated_stocks} hisse için {result.added_bars:,} yeni bar eklendi."
            self.syncNotification.emit(True, msg)
            self.dataSynced.emit()
        else:
            logger.info("MarketSyncController: %s", result.message)

    def _on_sync_failed(self, error_msg: str) -> None:
        self._is_syncing = False
        self.isSyncingChanged.emit()
        self._status_text = f"Güncelleme hatası: {error_msg}"
        self.statusTextChanged.emit()
        self.syncNotification.emit(False, f"Piyasa verisi güncellenemedi: {error_msg}")

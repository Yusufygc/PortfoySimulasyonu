"""
PriceRefreshController — fiyat güncellemesinin tek koordinatörü (QML: priceRefreshController).

Fiyatı yazan yollar ayrı denetleyicilerde çalışır ve ağ işini kendi arka plan yürütücülerinde yapar:
- `MarketSyncController`: kapanış barları (açılışta ve kapanış verisi hazır olunca; tüm BIST, SQLite köprüsü)
- `SystemController`: seans içinde aralıklı canlı fiyat (`latest_prices`)
- `StartupJobsController`: BIST dışı pozisyonların kapanış tamamlaması

Bu sınıf onların "fiyat yazıldı" sinyallerini tek bir `pricesChanged` sinyalinde birleştirir (art arda gelen
sinyaller tek yenilemeye iner); ekranlar (Ana Sayfa, İzleme Listesi, Model Portföy) yalnızca bu sinyalle ve yalnızca
veritabanından yeniden okur, kendileri ağ çağrısı yapmaz. Ekranlardaki küçük durum bileşeni son güncelleme zamanını
ve meşguliyeti buradan okur; tek yenile ikonu `refreshNow` çağırır (seans içinde canlı fiyat, dışında kapanış senkronu).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from src.ui_qml.last_update_store import LastUpdateStore, format_last_update

logger = logging.getLogger(__name__)


class PriceRefreshController(QObject):
    """QML context property: priceRefreshController"""

    # Fiyatlar veritabanında değişti: ekranlar DB'den yeniden okur (birleştirilmiş)
    pricesChanged = Signal()
    busyChanged = Signal()
    lastUpdateChanged = Signal()

    # Art arda gelen kaynak sinyallerinin tek yenilemeye indiği bekleme süresi
    COALESCE_MS = 400

    def __init__(self, system_ctrl=None, market_sync_ctrl=None, container=None, parent: QObject | None = None,
                 store: LastUpdateStore | None = None) -> None:
        super().__init__(parent)
        self._system = system_ctrl
        self._market_sync = market_sync_ctrl
        self._store = store or LastUpdateStore()
        self._last_update: Optional[datetime] = self._store.prices_last_update()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(self.COALESCE_MS)
        self._timer.timeout.connect(self.pricesChanged)
        self._connect_busy_sources()
        event_bus = getattr(container, "event_bus", None) if container is not None else None
        if event_bus is not None:
            try:
                # Arka plan iş parçacığından yayınlanabilir; sinyal-yuva bağlantısı ana iş parçacığına kuyruklar
                event_bus.prices_updated.connect(self._on_event_bus_prices)
            except Exception as exc:
                logger.warning("EventBus bağlantı hatası: %s", exc)

    def _connect_busy_sources(self) -> None:
        if self._system is not None:
            self._system.busyChanged.connect(self.busyChanged)
        if self._market_sync is not None:
            self._market_sync.isSyncingChanged.connect(self.busyChanged)

    # ------------------------------------------------------------------ kaynaklar

    def watch(self, signal, records_update: bool = True) -> None:
        """Bir "fiyat/portföy verisi değişti" sinyalini birleştirilmiş yenilemeye bağlar.

        records_update: kaynak yeni fiyat yazıyorsa son güncelleme zamanı kaydedilir (portföy değişikliğinde değil).
        """
        signal.connect(self.notifyPricesWritten if records_update else self.notifyDataChanged)

    @Slot()
    def notifyPricesWritten(self) -> None:
        self._last_update = self._store.save_prices_last_update()
        self.lastUpdateChanged.emit()
        self._schedule()

    @Slot()
    def notifyDataChanged(self) -> None:
        self._schedule()

    def _on_event_bus_prices(self, prices) -> None:
        if prices:
            self.notifyPricesWritten()

    def _schedule(self) -> None:
        if not self._timer.isActive():  # yeniden başlatılmaz: en geç COALESCE_MS sonra yenilenir
            self._timer.start()

    # ------------------------------------------------------------------ QML

    @Property(bool, notify=busyChanged)
    def isRefreshing(self) -> bool:
        system_busy = bool(self._system is not None and self._system.isRefreshing)
        sync_busy = bool(self._market_sync is not None and self._market_sync.isSyncing)
        return system_busy or sync_busy

    @Property(str, notify=lastUpdateChanged)
    def lastUpdateText(self) -> str:
        return format_last_update(self._last_update)

    @Slot()
    def refreshNow(self) -> None:
        """Tek yenile ikonu: seans açıksa canlı fiyat, değilse eksik kapanışlar için artımlı senkron."""
        if self.isRefreshing:
            return
        if self._system is not None and self._system.session_open():
            self._system.start_refresh()
        elif self._market_sync is not None:
            self._market_sync.triggerSyncNow()

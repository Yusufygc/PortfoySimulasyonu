"""Uygulama olay yolu: arayüz çerçevesinden (Qt) bağımsız yayın/abone.

Abone işlevleri yayının yapıldığı iş parçacığında çağrılır. Arayüz katmanı ana iş parçacığına geçmek için kendi
Qt sinyaline aktarır (bkz. `PriceRefreshController`); uygulama katmanı Qt import etmez.
"""
from __future__ import annotations

import logging
import threading
from typing import Callable, List

logger = logging.getLogger(__name__)


class Event:
    """`connect(abone)` ve `emit(yük)` sunan basit olay; bir abonenin hatası diğerlerini etkilemez."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._subscribers: List[Callable[[object], None]] = []
        self._lock = threading.Lock()

    def connect(self, subscriber: Callable[[object], None]) -> None:
        with self._lock:
            self._subscribers.append(subscriber)

    def disconnect(self, subscriber: Callable[[object], None]) -> None:
        with self._lock:
            if subscriber in self._subscribers:
                self._subscribers.remove(subscriber)

    def emit(self, payload: object) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            try:
                subscriber(payload)
            except Exception as exc:
                logger.warning("%s abonesi hata verdi: %s", self._name, exc, exc_info=True)


class GlobalEventBus:
    """Uygulama geneli olaylar. `prices_updated` yükü: `dict[int, Decimal]` (stock_id -> fiyat)."""

    def __init__(self) -> None:
        self.prices_updated = Event("prices_updated")

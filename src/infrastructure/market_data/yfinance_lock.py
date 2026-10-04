"""yfinance çağrıları için paylaşılan, zaman aşımlı serileştirme kapısı.

Etkileşimli sağlayıcılar (tek fiyat, değerleme, gösterge, optimizasyon, istemci) birbirini seri hale getirmek için
bu kapıyı `with yfinance_lock:` ile kullanır. Toplu BIST indirmeleri (`BistBulkDownloader`,
`MarketDataSyncService`) kapıyı kullanmaz.

Kapı **açılmaya dayanıklıdır (fail-open)**: kilit `LOCK_WAIT_TIMEOUT_SECONDS` içinde alınamazsa (tutan çağrı
takılmış demektir) uyarı yazılır ve çağrı kilitsiz devam eder; böylece tek bir takılan istek tüm yfinance
kullanıcılarını sonsuza dek bekletmez. yfinance 1.7.0 indirme yolu paylaşılan küresel durum kullanmadığından
kilitsiz devam güvenlidir (toplu indirmeler zaten kilitsiz ve eşzamanlı çalışır).
"""
from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger(__name__)

LOCK_WAIT_TIMEOUT_SECONDS = 30.0
SLOW_WAIT_LOG_SECONDS = 2.0


class YFinanceGate:
    def __init__(self, timeout: float = LOCK_WAIT_TIMEOUT_SECONDS) -> None:
        self._lock = threading.Lock()
        self._timeout = timeout
        self._local = threading.local()

    def __enter__(self) -> "YFinanceGate":
        started = time.monotonic()
        acquired = self._lock.acquire(timeout=self._timeout)
        waited = time.monotonic() - started
        if not acquired:
            logger.warning("yfinance kapısı %.0f sn içinde alınamadı; çağrı kilitsiz sürdürülüyor.", waited)
        elif waited >= SLOW_WAIT_LOG_SECONDS:
            logger.info("yfinance kapısı %.1f sn beklendi.", waited)
        stack = getattr(self._local, "stack", None)
        if stack is None:
            stack = self._local.stack = []
        stack.append(acquired)
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._local.stack.pop():
            self._lock.release()


yfinance_lock = YFinanceGate()

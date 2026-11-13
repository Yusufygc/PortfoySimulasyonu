"""Ağ çağrıları için ortak yeniden deneme (üstel geri çekilme) yardımcısı.

Yalnızca geçici hatalar (bağlantı/zaman aşımı, HTTP 408/429/5xx, yfinance hız sınırı) yeniden denenir.
Kalıcı hatalar (4xx, ayrıştırma, bilinmeyen sembol) ilk denemede çağırana döner.
"""
from __future__ import annotations

import logging
import socket
import time
import urllib.error
from typing import Callable, TypeVar

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

try:
    from yfinance.exceptions import YFRateLimitError
except ImportError:  # pragma: no cover
    YFRateLimitError = None

logger = logging.getLogger(__name__)

T = TypeVar("T")

DEFAULT_ATTEMPTS = 3
DEFAULT_BASE_DELAY_SECONDS = 1.0
_TRANSIENT_HTTP_STATUS = frozenset({408, 429, 500, 502, 503, 504})

# Testler bu referansı değiştirerek gerçek bekleme olmadan çalışır.
_sleep: Callable[[float], None] = time.sleep


def is_transient_error(exc: BaseException) -> bool:
    """Hata geçici bir ağ/sunucu sorunu ise True döner."""
    if isinstance(exc, urllib.error.HTTPError):  # URLError alt sınıfı, önce bakılmalı
        return exc.code in _TRANSIENT_HTTP_STATUS
    if isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError, socket.timeout)):
        return True
    if requests is not None:
        if isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
            return True
        if isinstance(exc, requests.exceptions.HTTPError):
            status = getattr(exc.response, "status_code", None)
            return status in _TRANSIENT_HTTP_STATUS
    return YFRateLimitError is not None and isinstance(exc, YFRateLimitError)


def raise_for_transient_status(response) -> None:
    """requests yanıtı geçici bir HTTP durumundaysa (429/5xx) `HTTPError` fırlatır; aksi halde bir şey yapmaz."""
    if getattr(response, "status_code", None) in _TRANSIENT_HTTP_STATUS:
        response.raise_for_status()


def retry_call(
    operation: Callable[[], T],
    *,
    attempts: int = DEFAULT_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY_SECONDS,
    is_retryable: Callable[[BaseException], bool] = is_transient_error,
    label: str = "",
) -> T:
    """`operation`'ı çağırır; geçici hatada `base_delay * 2**n` saniye bekleyip tekrar dener.

    Son denemede veya kalıcı hatada özgün istisna yeniden fırlatılır.
    """
    if attempts < 1:
        raise ValueError("attempts en az 1 olmalı")
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as exc:
            if attempt == attempts or not is_retryable(exc):
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning("%s geçici hata (deneme %d/%d), %.1f sn sonra tekrar: %s", label or "Ağ çağrısı", attempt, attempts, delay, exc)
            _sleep(delay)
    raise AssertionError("ulaşılamaz")  # pragma: no cover

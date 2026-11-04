"""Haber sağlayıcılarının ortak HTTP yardımcıları.

Yanıt durumu açıkça denetlenir: 4xx/5xx, boş gövde ve ağ hatası `NewsProviderUnavailable` olur
(yfinance'in sessiz boş dönüşü bu katmanda tekrarlanmaz). Geçici hatalar `retry_call` ile yeniden denenir.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import requests

from src.domain.ports.services.i_news_provider import NewsProviderUnavailable
from src.infrastructure.retry import raise_for_transient_status, retry_call

DEFAULT_TIMEOUT_SECONDS = 15
MAX_BODY_BYTES = 4 * 1024 * 1024  # Hürriyet gibi büyük akışlar için üst sınır

BROWSER_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
}

# Test ve çevrimdışı çalışma için enjekte edilebilir imzalar.
GetFetcher = Callable[[str], bytes]
PostFetcher = Callable[[str, Dict[str, Any], Dict[str, str]], bytes]


def _read_limited(response: requests.Response) -> bytes:
    """Gövdeyi `MAX_BODY_BYTES` sınırına kadar akışla okur; sınırdan büyük yanıtın tamamı belleğe alınmaz."""
    chunks, size = [], 0
    try:
        for chunk in response.iter_content(chunk_size=64 * 1024):
            chunks.append(chunk)
            size += len(chunk)
            if size >= MAX_BODY_BYTES:
                break
    finally:
        response.close()
    return b"".join(chunks)[:MAX_BODY_BYTES]


def _check(response: requests.Response, label: str) -> bytes:
    try:
        raise_for_transient_status(response)
    except Exception:
        response.close()
        raise
    if response.status_code != 200:
        response.close()
        raise NewsProviderUnavailable(f"{label}: HTTP {response.status_code}")
    content = _read_limited(response)
    if not content.strip():
        raise NewsProviderUnavailable(f"{label}: boş yanıt")
    return content


def http_get(url: str, label: str = "Haber", headers: Optional[Dict[str, str]] = None) -> bytes:
    def call() -> bytes:
        response = requests.get(
            url, headers={**BROWSER_HEADERS, **(headers or {})}, timeout=DEFAULT_TIMEOUT_SECONDS, stream=True
        )
        return _check(response, label)

    try:
        return retry_call(call, label=label)
    except NewsProviderUnavailable:
        raise
    except Exception as exc:
        raise NewsProviderUnavailable(f"{label}: {type(exc).__name__}: {exc}") from exc


def http_post_json(url: str, body: Dict[str, Any], headers: Dict[str, str], label: str = "Haber") -> bytes:
    def call() -> bytes:
        response = requests.post(
            url, json=body, headers={**BROWSER_HEADERS, **headers}, timeout=DEFAULT_TIMEOUT_SECONDS, stream=True
        )
        return _check(response, label)

    try:
        return retry_call(call, label=label)
    except NewsProviderUnavailable:
        raise
    except Exception as exc:
        raise NewsProviderUnavailable(f"{label}: {type(exc).__name__}: {exc}") from exc

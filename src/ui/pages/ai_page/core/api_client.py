# -*- coding: utf-8 -*-
"""
AI_Core (ts_forecasting_lab) FastAPI servisi ile haberleşen HTTP istemcisi.

Kullanım:
    client = AICoreFastAPIClient(base_url="http://localhost:8000")
    if client.health_check():
        data = client.get_analysis("THYAO")
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# Varsayılan değerler
_DEFAULT_BASE_URL = "http://localhost:8000"
_DEFAULT_TIMEOUT = 15  # saniye


class APIConnectionError(Exception):
    """FastAPI sunucusuna bağlanılamadığında fırlatılır."""
    pass


class APIResponseError(Exception):
    """Sunucu başarısız HTTP durum kodu döndürdüğünde fırlatılır."""

    def __init__(self, status_code: int, detail: str = ""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class AICoreFastAPIClient:
    """ts_forecasting_lab FastAPI servisiyle haberleşen HTTP istemcisi."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        raw_url = base_url or os.getenv("AI_CORE_API_URL", _DEFAULT_BASE_URL)
        self.base_url = raw_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    # ─────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────

    def health_check(self) -> bool:
        """GET /health — servis erişilebilir mi?

        Bağlantı hatasında veya sunucu hatalarında False döner;
        istisnayı yutarak UI tarafında fallback mekanizmasına izin verir.
        """
        try:
            resp = self._get("/health")
            return resp.get("status") in ("ok", "degraded")
        except Exception:
            logger.debug("AI_Core health check başarısız", exc_info=True)
            return False

    def get_analysis(self, symbol: str) -> Dict[str, Any]:
        """GET /analysis/{symbol} — tam analiz payload'unu döner.

        Raises:
            APIConnectionError: Sunucuya bağlanılamadığında.
            APIResponseError: HTTP 4xx/5xx döndüğünde.
        """
        return self._get(f"/analysis/{symbol.upper()}")

    def get_symbols(self) -> List[str]:
        """GET /symbols — kayıtlı hisse kodlarını döner.

        Raises:
            APIConnectionError, APIResponseError
        """
        data = self._get("/symbols")
        return data.get("symbols", [])

    def get_best_model(self, symbol: str) -> Dict[str, Any]:
        """GET /best-model/{symbol} — en iyi model bilgisini döner."""
        return self._get(f"/best-model/{symbol.upper()}")

    def get_leaderboard(self, top_n: int = 20) -> Dict[str, Any]:
        """GET /leaderboard — hisseler arası lider tablosu."""
        return self._get("/leaderboard", params={"top_n": top_n})

    # ─────────────────────────────────────────────────────────────────────
    # Internal
    # ─────────────────────────────────────────────────────────────────────

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET isteği gönderir; hata yönetimini merkezleştirir."""
        url = f"{self.base_url}{path}"
        try:
            resp = self._session.get(url, params=params, timeout=self.timeout)
        except requests.ConnectionError as exc:
            logger.warning("AI_Core connection failed: url=%s", url, exc_info=True)
            raise APIConnectionError(
                f"AI_Core sunucusuna bağlanılamadı ({url}). "
                "Sunucunun çalıştığından emin olun: "
                "uvicorn src.api.main:app --port 8000"
            ) from exc
        except requests.Timeout as exc:
            logger.warning("AI_Core request timed out: url=%s timeout=%s", url, self.timeout, exc_info=True)
            raise APIConnectionError(
                f"AI_Core isteği zaman aşımına uğradı ({self.timeout}s): {url}"
            ) from exc

        if resp.status_code >= 400:
            detail = ""
            try:
                body = resp.json()
                detail = body.get("detail", str(body))
            except Exception:
                detail = resp.text[:200]
            logger.error("AI_Core response error: url=%s status_code=%s detail=%s", url, resp.status_code, detail)
            raise APIResponseError(resp.status_code, detail)

        try:
            return resp.json()
        except ValueError as exc:
            logger.error("AI_Core returned invalid JSON: url=%s", url, exc_info=True)
            raise APIResponseError(resp.status_code, "Invalid JSON response") from exc

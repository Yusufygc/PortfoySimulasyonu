"""
ShareholderAnalysisService — KAP ortaklık yapısı orkestrasyon servisi.

Dış API'yi doğrudan çağırmaz (ARCHITECTURE_GATES §15).
IShareholderProvider arayüzü üzerinden KAP'a erişir; tarihçeyi
IShareholderRepository ile MySQL'de saklar.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from src.domain.models.shareholder import ShareholderSnapshot
from src.domain.ports.repositories.i_shareholder_repo import IShareholderRepository
from src.domain.ports.services.i_shareholder_provider import (
    IShareholderProvider,
    ShareholderProviderUnavailable,
)

logger = logging.getLogger(__name__)

_REFRESH_TTL_HOURS = 24


class ShareholderAnalysisService:
    """KAP pay sahipliği analiz orkestrasyonu."""

    def __init__(
        self,
        provider: IShareholderProvider,
        repository: IShareholderRepository,
    ) -> None:
        self._provider   = provider
        self._repository = repository

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_history(
        self,
        ticker: str,
        force_refresh: bool = False,
    ) -> list[ShareholderSnapshot]:
        """
        Ticker için pay sahipliği tarihçesini döndür.

        TTL içinde DB'den okur, dışındaysa KAP'tan yeniler.
        force_refresh=True ise her zaman KAP'a gider.
        """
        ticker = ticker.strip().upper()
        if not force_refresh and self._cache_fresh(ticker):
            cached = self._repository.get_shareholder_history(ticker)
            if cached:
                logger.info("KAP tarihçe cache'ten okundu: %s (%d snapshot)", ticker, len(cached))
                return cached
        return self._refresh(ticker)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _refresh(self, ticker: str) -> list[ShareholderSnapshot]:
        """KAP'tan canlı çek + DB'ye yaz."""
        logger.info("KAP tarihçe yenileniyor: %s", ticker)
        oid, title = self._resolve_oid(ticker)
        snapshots = self._provider.get_shareholder_history(ticker)
        self._repository.upsert_company(ticker, oid, title)
        self._repository.replace_shareholder_history(ticker, snapshots)
        logger.info(
            "KAP tarihçe kaydedildi: %s (%d snapshot)", ticker, len(snapshots)
        )
        return snapshots

    def _resolve_oid(self, ticker: str) -> tuple[str, Optional[str]]:
        """OID ve title'ı al — provider üzerinden BIST haritasından çözer."""
        resolver = getattr(self._provider, "resolve_member_oid", None)
        if callable(resolver):
            return resolver(ticker)
        cached_oid = self._repository.get_mkk_oid(ticker)
        if cached_oid:
            return cached_oid, None
        raise ShareholderProviderUnavailable(
            f"{ticker}: KAP OID çözülemedi (resolver yok ve DB cache boş)"
        )

    def _cache_fresh(self, ticker: str) -> bool:
        last = self._repository.get_last_fetched_at(ticker)
        if last is None:
            return False
        return (datetime.utcnow() - last) < timedelta(hours=_REFRESH_TTL_HOURS)

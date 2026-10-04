"""Stock 360 uzak veri akışı: hisse kataloğu keşfi ve arka plan finansal / KAP veri çekimi.

Denetleyici durumundan bağımsız saf fonksiyonlardır; yalnızca verilen servis ve kapla çalışır.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.domain.models.shareholder import ShareholderSnapshot
from src.ui_qml.controllers.stock_360_html import (
    generate_financials_html,
    generate_shareholders_html,
    write_temp_html,
)

logger = logging.getLogger(__name__)

DEFAULT_CANDIDATES = ["BIMAS", "ADEL", "AKCNS", "ALBRK", "AYGAZ", "BRSAN", "CLEBI", "THYAO", "ASELS", "KCHOL"]
_AVAILABLE_LIMIT = 12


@dataclass
class RemoteResult:
    """Arka plan çekiminin sonucu; UI iş parçacığına tek nesne olarak iletilir."""

    ticker: str
    financials: Optional[Dict[str, Any]]
    shareholders: Optional[List[ShareholderSnapshot]]
    fin_html_url: str
    sh_html_url: str
    error: str
    temp_files: List[str] = field(default_factory=list)

    def as_tuple(self) -> tuple:
        return (self.ticker, self.financials, self.shareholders, self.fin_html_url, self.sh_html_url, self.error)


def _stock_service(container: Any) -> Any:
    service = getattr(container, "stock_360_service", None)
    if not service and hasattr(container, "services"):
        service = getattr(container.services, "stock_360_service", None)
    return service


def _catalog_tickers(service: Any) -> List[str]:
    """DuckDB piyasa kataloğu (tüm BIST); servis yoksa ya da katalog boşsa boş liste."""
    catalog = service.get_catalog_tickers() if service and hasattr(service, "get_catalog_tickers") else []
    return [str(t) for t in catalog] if isinstance(catalog, list) else []


def _stored_stocks(container: Any, service: Any) -> List[Any]:
    if service and hasattr(service, "get_all_stocks"):
        return service.get_all_stocks()
    if getattr(container, "stock_lookup_service", None) is not None:
        return container.stock_lookup_service.list_stocks()
    return []


def _discover_tickers(container: Any) -> List[str]:
    service = _stock_service(container)
    catalog = _catalog_tickers(service)
    if catalog:
        return catalog
    # Katalog yoksa SQLite'taki hisseler
    return [s.ticker.replace(".IS", "") for s in _stored_stocks(container, service) if getattr(s, "ticker", None)]


def rank_tickers(tickers: List[str]) -> List[str]:
    """Öncelikli adayları öne alıp kalanları sırasıyla ekler; ilk 12'yi döndürür."""
    ranked = [c for c in DEFAULT_CANDIDATES if c in tickers]
    ranked.extend(t for t in tickers if t not in ranked)
    return ranked[:_AVAILABLE_LIMIT]


def discover_available_stocks(container: Any) -> List[str]:
    """Hızlı seçim hisseleri: katalog/portföy hisseleri, bulunamazsa varsayılan adaylar."""
    if container:
        try:
            tickers = _discover_tickers(container)
            if tickers:
                return rank_tickers(tickers)
        except Exception as exc:
            logger.warning("Available stocks yüklenirken hata: %s", exc)
    return list(DEFAULT_CANDIDATES)


def fetch_remote_data(service: Any, ticker: str, periods_count: int, force_refresh_shareholders: bool) -> RemoteResult:
    """Ağ üzerinden finansal bilanço ve KAP ortaklık verilerini çeker, HTML panolarını geçici dosyaya yazar."""
    result = RemoteResult(ticker, None, None, "", "", "")
    if not service:
        return result

    # 1. Finansallar
    try:
        result.financials = service.get_financials(ticker, n_quarters=12)
        if result.financials:
            n_p = len(result.financials.get("periods", [])) if periods_count == 0 else periods_count
            html = generate_financials_html(result.financials, n_periods=n_p)
            result.fin_html_url = _write_html(result, f"fin_{periods_count}", ticker, html)
    except Exception as exc:
        logger.warning("Finansal veri çekilemedi [%s]: %s", ticker, exc)
        result.error = f"Finansal veriler alınamadı ({exc})"

    # 2. KAP Ortaklık
    try:
        result.shareholders = service.get_shareholders(ticker, force_refresh=force_refresh_shareholders)
        if result.shareholders:
            html = generate_shareholders_html(ticker, result.shareholders)
            result.sh_html_url = _write_html(result, "sh", ticker, html)
    except Exception as exc:
        logger.warning("KAP ortaklık verisi çekilemedi [%s]: %s", ticker, exc)

    return result


def _write_html(result: RemoteResult, prefix: str, ticker: str, html: str) -> str:
    url, file_path = write_temp_html(prefix, ticker, html)
    if file_path:
        result.temp_files.append(file_path)
    return url

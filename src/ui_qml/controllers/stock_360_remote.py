"""Stock 360 uzak veri akışı: arka plan finansal / KAP veri çekimi.

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
from src.ui_qml.messages import msg

logger = logging.getLogger(__name__)


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
        result.error = msg("stock360.finansal_veriler_alinamadi", exc=exc)

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

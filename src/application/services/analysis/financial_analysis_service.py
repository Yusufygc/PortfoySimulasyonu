"""
FinancialAnalysisService — finansal tablo analiz orkestrasyon servisi.

Dış API'yi doğrudan çağırmaz (ARCHITECTURE_GATES §15).
IFinancialStatementProvider arayüzü üzerinden sağlayıcıya erişir.
"""
from __future__ import annotations

import logging
from typing import Any

from src.domain.ports.services.i_financial_statement_provider import (
    IFinancialStatementProvider,
    FinancialStatementProviderUnavailable,
)
from src.application.services.analysis.financials.metrics import compute_metrics

logger = logging.getLogger(__name__)


class FinancialAnalysisService:
    """Bilanço ve Finansallar analiz servisi."""

    def __init__(self, financial_statement_provider: IFinancialStatementProvider) -> None:
        self._provider = financial_statement_provider

    def analyze(
        self,
        ticker: str,
        n_quarters: int = 12,
        currency: str = "TRY",
    ) -> dict[str, Any]:
        """
        Ticker için finansal analiz yap.

        Args:
            ticker:     BIST kodu (ör: "FROTO").
            n_quarters: Kaç çeyrek veri çekilsin.
            currency:   Para birimi ("TRY" veya "USD").

        Returns:
            compute_metrics() çıktısı; 'ticker', 'periods', tüm metrik serileri dahil.

        Raises:
            FinancialStatementProviderUnavailable: veri alınamadığında.
        """
        logger.info("FinancialAnalysisService.analyze: %s (%dQ, %s)", ticker, n_quarters, currency)
        raw = self._provider.get_financial_data(
            ticker=ticker,
            n_quarters=n_quarters,
            currency=currency,
        )
        metrics = compute_metrics(raw)
        logger.info(
            "Analiz tamamlandı: %s — %d dönem, metrik sayısı: %d",
            ticker,
            len(metrics.get("periods", [])),
            len(metrics),
        )
        return metrics

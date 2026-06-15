"""
FinancialAnalysisService — finansal tablo analiz orkestrasyon servisi.

Dış API'yi doğrudan çağırmaz (ARCHITECTURE_GATES §15).
IFinancialStatementProvider arayüzü üzerinden sağlayıcıya erişir.
Opsiyonel: IInflationDataProvider (TÜFE), IMarketValuationProvider (piyasa değeri).
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional

from src.domain.ports.services.i_financial_statement_provider import (
    IFinancialStatementProvider,
    FinancialStatementProviderUnavailable,
)
from src.application.services.analysis.financials.metrics import compute_metrics
from src.application.services.analysis.financials.valuation import compute_valuation

logger = logging.getLogger(__name__)

_TUFE_LOOKBACK_YEARS = 6


class FinancialAnalysisService:
    """Bilanço ve Finansallar analiz servisi."""

    def __init__(
        self,
        financial_statement_provider: IFinancialStatementProvider,
        inflation_provider: Optional[Any] = None,
        valuation_provider: Optional[Any] = None,
    ) -> None:
        self._provider           = financial_statement_provider
        self._inflation_provider = inflation_provider
        self._valuation_provider = valuation_provider

    def analyze(
        self,
        ticker: str,
        n_quarters: int = 12,
        currency: str = "TRY",
    ) -> dict[str, Any]:
        """
        Ticker için finansal analiz yap.

        Returns:
            compute_metrics() çıktısı; opsiyonel _tufe ve _market_val enjekte edilir.

        Raises:
            FinancialStatementProviderUnavailable: veri alınamadığında.
        """
        logger.info("FinancialAnalysisService.analyze: %s (%dQ, %s)", ticker, n_quarters, currency)
        raw     = self._provider.get_financial_data(
            ticker=ticker, n_quarters=n_quarters, currency=currency,
        )
        metrics = compute_metrics(raw)
        self._enrich_tufe(metrics)
        self._enrich_valuation(metrics, ticker)
        logger.info(
            "Analiz tamamlandı: %s — %d dönem",
            ticker, len(metrics.get("periods", [])),
        )
        return metrics

    def _enrich_tufe(self, metrics: dict[str, Any]) -> None:
        """TÜFE endeksini metrics['_tufe'] olarak enjekte et. Hata sessiz."""
        if self._inflation_provider is None:
            return
        periods = metrics.get("periods", [])
        if not periods:
            return
        try:
            today = date.today()
            start = date(today.year - _TUFE_LOOKBACK_YEARS, 1, 1)
            tufe  = self._inflation_provider.get_monthly_tufe(start, today)
            if tufe:
                metrics["_tufe"] = tufe
        except Exception as exc:
            logger.warning("TÜFE enrich atlandı: %s", exc)
            metrics["_tufe_error"] = str(exc)

    def _enrich_valuation(self, metrics: dict[str, Any], ticker: str) -> None:
        """Piyasa değerlemesini metrics['_market_val'] olarak enjekte et. Hata sessiz."""
        if self._valuation_provider is None:
            return
        try:
            snap = self._valuation_provider.get_market_snapshot(ticker)
            val  = compute_valuation(metrics, snap)
            metrics["_market_val"] = val
        except Exception as exc:
            logger.warning("Değerleme enrich atlandı [%s]: %s", ticker, exc)

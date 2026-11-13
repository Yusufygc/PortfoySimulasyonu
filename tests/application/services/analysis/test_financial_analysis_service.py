"""FinancialAnalysisService birim testleri — mock provider ile."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.application.services.analysis.financial_analysis_service import FinancialAnalysisService
from src.domain.ports.services.i_financial_statement_provider import (
    FinancialStatementProviderUnavailable,
)


_FAKE_RAW = {
    "ticker": "FROTO",
    "currency": "TRY",
    "periods": ["2024/3", "2023/12"],
    "sections": {
        "bilanco": {}, "gelir": {}, "dipnot": {}, "nakit_akim": {},
    },
}

_FAKE_METRICS = {
    "ticker": "FROTO",
    "currency": "TRY",
    "periods": ["2024/3", "2023/12"],
    "satis": {}, "net_kar": {},
}


def _make_provider(return_value=None, side_effect=None) -> MagicMock:
    provider = MagicMock()
    if side_effect is not None:
        provider.get_financial_data.side_effect = side_effect
    else:
        provider.get_financial_data.return_value = return_value or _FAKE_RAW
    return provider


class TestFinancialAnalysisServiceAnalyze:
    """analyze() metodu testleri."""

    def test_calls_provider_with_correct_args(self):
        provider = _make_provider()
        with patch(
            "src.application.services.analysis.financial_analysis_service.compute_metrics",
            return_value=dict(_FAKE_METRICS),
        ):
            service = FinancialAnalysisService(financial_statement_provider=provider)
            service.analyze("FROTO", n_quarters=8, currency="TRY")

        provider.get_financial_data.assert_called_once_with(
            ticker="FROTO", n_quarters=8, currency="TRY",
        )

    def test_returns_compute_metrics_output(self):
        provider = _make_provider()
        with patch(
            "src.application.services.analysis.financial_analysis_service.compute_metrics",
            return_value=dict(_FAKE_METRICS),
        ) as mock_compute:
            service = FinancialAnalysisService(financial_statement_provider=provider)
            result = service.analyze("FROTO")

        mock_compute.assert_called_once_with(_FAKE_RAW)
        assert result["ticker"] == "FROTO"

    def test_uses_default_n_quarters_and_currency(self):
        provider = _make_provider()
        with patch(
            "src.application.services.analysis.financial_analysis_service.compute_metrics",
            return_value=dict(_FAKE_METRICS),
        ):
            service = FinancialAnalysisService(financial_statement_provider=provider)
            service.analyze("AKBNK")

        provider.get_financial_data.assert_called_once_with(
            ticker="AKBNK", n_quarters=12, currency="TRY",
        )

    def test_propagates_provider_unavailable(self):
        provider = _make_provider(side_effect=FinancialStatementProviderUnavailable("ağ hatası"))
        service = FinancialAnalysisService(financial_statement_provider=provider)

        with pytest.raises(FinancialStatementProviderUnavailable, match="ağ hatası"):
            service.analyze("THYAO")

    def test_propagates_unexpected_errors(self):
        provider = _make_provider(side_effect=RuntimeError("beklenmedik"))
        service = FinancialAnalysisService(financial_statement_provider=provider)

        with pytest.raises(RuntimeError, match="beklenmedik"):
            service.analyze("BIMAS")


class TestFinancialAnalysisServiceEnrichment:
    """_enrich_tufe ve _enrich_valuation testleri."""

    def _make_service(self, inflation_provider=None, valuation_provider=None):
        return FinancialAnalysisService(
            financial_statement_provider=_make_provider(),
            inflation_provider=inflation_provider,
            valuation_provider=valuation_provider,
        )

    def test_enrich_tufe_injects_when_provider_given(self):
        tufe_data = {"2024-01": 1402.0, "2023-01": 1180.0}
        inf_prov  = MagicMock()
        inf_prov.get_monthly_tufe.return_value = tufe_data

        with patch(
            "src.application.services.analysis.financial_analysis_service.compute_metrics",
            return_value=dict(_FAKE_METRICS),
        ):
            svc    = self._make_service(inflation_provider=inf_prov)
            result = svc.analyze("FROTO")

        assert result.get("_tufe") == tufe_data

    def test_enrich_tufe_graceful_on_error(self):
        inf_prov = MagicMock()
        inf_prov.get_monthly_tufe.side_effect = Exception("API down")

        with patch(
            "src.application.services.analysis.financial_analysis_service.compute_metrics",
            return_value=dict(_FAKE_METRICS),
        ):
            svc    = self._make_service(inflation_provider=inf_prov)
            result = svc.analyze("FROTO")

        assert "_tufe" not in result

    def test_enrich_tufe_skipped_when_no_provider(self):
        with patch(
            "src.application.services.analysis.financial_analysis_service.compute_metrics",
            return_value=dict(_FAKE_METRICS),
        ):
            svc    = self._make_service()
            result = svc.analyze("FROTO")

        assert "_tufe" not in result

    def test_enrich_valuation_injects_when_provider_given(self):
        snap    = {"market_cap": 1e12, "price": 1000.0, "shares_outstanding": 1e9, "error": None}
        val_prov = MagicMock()
        val_prov.get_market_snapshot.return_value = snap

        with patch(
            "src.application.services.analysis.financial_analysis_service.compute_metrics",
            return_value=dict(_FAKE_METRICS),
        ):
            svc    = self._make_service(valuation_provider=val_prov)
            result = svc.analyze("FROTO")

        assert "_market_val" in result
        val_prov.get_market_snapshot.assert_called_once_with("FROTO")

    def test_enrich_valuation_graceful_on_error(self):
        val_prov = MagicMock()
        val_prov.get_market_snapshot.side_effect = Exception("yfinance down")

        with patch(
            "src.application.services.analysis.financial_analysis_service.compute_metrics",
            return_value=dict(_FAKE_METRICS),
        ):
            svc    = self._make_service(valuation_provider=val_prov)
            result = svc.analyze("FROTO")

        assert "_market_val" not in result

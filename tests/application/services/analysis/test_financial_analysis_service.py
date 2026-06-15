"""FinancialAnalysisService birim testleri — mock provider ile."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from src.application.services.analysis.financial_analysis_service import FinancialAnalysisService
from src.domain.ports.services.i_financial_statement_provider import (
    FinancialStatementProviderUnavailable,
)


_FAKE_RAW = {
    "ticker": "FROTO",
    "currency": "TRY",
    "periods": ["2024/3", "2023/12"],
    "sections": {
        "bilanco": {},
        "gelir": {},
        "dipnot": {},
        "nakit_akim": {},
    },
}

_FAKE_METRICS = {
    "ticker": "FROTO",
    "currency": "TRY",
    "periods": ["2024/3", "2023/12"],
    "satis": [],
    "net_kar": [],
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
            return_value=_FAKE_METRICS,
        ):
            service = FinancialAnalysisService(financial_statement_provider=provider)
            service.analyze("FROTO", n_quarters=8, currency="TRY")

        provider.get_financial_data.assert_called_once_with(
            ticker="FROTO",
            n_quarters=8,
            currency="TRY",
        )

    def test_returns_compute_metrics_output(self):
        provider = _make_provider()
        with patch(
            "src.application.services.analysis.financial_analysis_service.compute_metrics",
            return_value=_FAKE_METRICS,
        ) as mock_compute:
            service = FinancialAnalysisService(financial_statement_provider=provider)
            result = service.analyze("FROTO")

        mock_compute.assert_called_once_with(_FAKE_RAW)
        assert result is _FAKE_METRICS

    def test_uses_default_n_quarters_and_currency(self):
        provider = _make_provider()
        with patch(
            "src.application.services.analysis.financial_analysis_service.compute_metrics",
            return_value=_FAKE_METRICS,
        ):
            service = FinancialAnalysisService(financial_statement_provider=provider)
            service.analyze("AKBNK")

        provider.get_financial_data.assert_called_once_with(
            ticker="AKBNK",
            n_quarters=12,
            currency="TRY",
        )

    def test_propagates_provider_unavailable(self):
        provider = _make_provider(
            side_effect=FinancialStatementProviderUnavailable("ağ hatası")
        )
        service = FinancialAnalysisService(financial_statement_provider=provider)

        with pytest.raises(FinancialStatementProviderUnavailable, match="ağ hatası"):
            service.analyze("THYAO")

    def test_propagates_unexpected_errors(self):
        provider = _make_provider(side_effect=RuntimeError("beklenmedik"))
        service = FinancialAnalysisService(financial_statement_provider=provider)

        with pytest.raises(RuntimeError, match="beklenmedik"):
            service.analyze("BIMAS")

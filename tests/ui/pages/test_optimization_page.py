from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6")

from src.domain.models.optimization_result import (
    OptimizationMetrics,
    OptimizationResult,
)
from src.ui.pages.optimization_page import OptimizationPage


class DummyOptimizationService:
    def get_model_portfolios(self):
        return []


def _page():
    return OptimizationPage(
        container=SimpleNamespace(optimization_service=DummyOptimizationService())
    )


def _result():
    metrics = OptimizationMetrics(
        expected_return=0.1,
        volatility=0.2,
        sharpe_ratio=0.5,
    )
    return OptimizationResult(
        current_metrics=metrics,
        optimized_metrics=metrics,
        suggestions=[],
    )


def test_optimization_success_clears_loading_state(qapp):
    page = _page()
    page._optimization_request_id = 1
    page._set_loading(True)

    page._on_optimization_finished(1, _result())

    assert page.btn_optimize.isEnabled() is True
    assert page.progress_bar.isVisible() is False


def test_optimization_error_clears_loading_state(monkeypatch, qapp):
    monkeypatch.setattr(
        "src.ui.pages.optimization_page.Toast.error",
        lambda *args, **kwargs: None,
    )
    page = _page()
    page._optimization_request_id = 1
    page._set_loading(True)

    page._on_optimization_error(1, (ValueError, ValueError("boom"), "trace"))

    assert page.btn_optimize.isEnabled() is True
    assert page.progress_bar.isVisible() is False

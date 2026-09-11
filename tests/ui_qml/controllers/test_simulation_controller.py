"""SimulationController — d5 SimulationView (DCA backtest) köprüsü testleri."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.application.services.simulation.dca_backtest import DCABacktestResult
from src.ui_qml.controllers.simulation_controller import SimulationController


def _result(
    series=None,
    total_invested="30000",
    final_value="26684",
    shares=None,
    total_return_pct=-11.05,
    contribution_count=30,
) -> DCABacktestResult:
    return DCABacktestResult(
        portfolio_value_series=series if series is not None else {
            date(2024, 1, 2): Decimal("1000"),
            date(2024, 2, 1): Decimal("1980"),
        },
        total_invested=Decimal(total_invested),
        final_value=Decimal(final_value),
        shares_by_ticker=shares if shares is not None else {"AKBNK": Decimal("12.5"), "FROTO": Decimal("3.2")},
        total_return_pct=total_return_pct,
        contribution_count=contribution_count,
    )


def _make_container(result=None, raises=None):
    container = MagicMock()
    if raises is not None:
        container.dca_backtest_service.run.side_effect = raises
    else:
        container.dca_backtest_service.run.return_value = result if result is not None else _result()
    return container


class TestInitialState:
    def test_no_result_until_run(self, qapp):
        controller = SimulationController(_make_container())
        assert controller.hasResult is False
        assert controller.errorMessage == ""

    def test_default_monthly_contribution_and_range(self, qapp):
        controller = SimulationController(_make_container())
        assert controller.monthlyContribution == 1000.0
        assert controller.selectedRangeKey == "3Y"

    def test_range_keys_and_labels(self, qapp):
        controller = SimulationController(_make_container())
        assert controller.rangeKeys == ["1Y", "3Y", "5Y", "MAX"]
        assert controller.rangeLabels == ["1 Yıl", "3 Yıl", "5 Yıl", "Tümü"]


class TestValidation:
    def test_empty_tickers_fails_without_calling_backend(self, qapp):
        container = _make_container()
        controller = SimulationController(container)

        controller.runSimulation()

        assert controller.hasResult is False
        assert "ticker" in controller.errorMessage.lower()
        container.dca_backtest_service.run.assert_not_called()

    def test_zero_contribution_fails(self, qapp):
        controller = SimulationController(_make_container())
        controller.setTickersText("AKBNK")
        controller.setMonthlyContribution(0.0)

        controller.runSimulation()

        assert controller.hasResult is False
        assert "katkı" in controller.errorMessage.lower()

    def test_empty_result_series_is_treated_as_failure(self, qapp):
        empty_result = _result(series={}, total_invested="0", final_value="0", shares={}, total_return_pct=None, contribution_count=0)
        controller = SimulationController(_make_container(result=empty_result))
        controller.setTickersText("YOK")

        controller.runSimulation()

        assert controller.hasResult is False
        assert controller.errorMessage != ""

    def test_backend_exception_is_captured(self, qapp):
        container = _make_container(raises=ValueError("hisse bulunamadi"))
        controller = SimulationController(container)
        controller.setTickersText("AKBNK")

        controller.runSimulation()

        assert controller.hasResult is False
        assert "hisse bulunamadi" in controller.errorMessage


class TestTickerParsing:
    def test_comma_separated_tickers_are_parsed_and_uppercased(self, qapp):
        container = _make_container()
        controller = SimulationController(container)
        controller.setTickersText(" akbnk, froto ,  ")

        controller.runSimulation()

        call = container.dca_backtest_service.run.call_args
        assert call.kwargs["tickers"] == ["AKBNK", "FROTO"]


class TestResult:
    def test_summary_fields_populated(self, qapp):
        controller = SimulationController(_make_container())
        controller.setTickersText("AKBNK, FROTO")
        controller.runSimulation()

        assert controller.hasResult is True
        assert controller.totalInvested == pytest.approx(30000.0)
        assert controller.finalValue == pytest.approx(26684.0)
        assert controller.totalReturnPct == pytest.approx(-11.05)
        assert controller.contributionCount == 30

    def test_series_sorted_chronologically(self, qapp):
        series = {
            date(2024, 3, 1): Decimal("3000"),
            date(2024, 1, 2): Decimal("1000"),
            date(2024, 2, 1): Decimal("2000"),
        }
        controller = SimulationController(_make_container(result=_result(series=series)))
        controller.setTickersText("AKBNK")
        controller.runSimulation()

        assert controller.portfolioValueSeries == [1000.0, 2000.0, 3000.0]

    def test_breakdown_from_shares_by_ticker(self, qapp):
        controller = SimulationController(_make_container())
        controller.setTickersText("AKBNK, FROTO")
        controller.runSimulation()

        assert controller.breakdownTickers == ["AKBNK", "FROTO"]
        assert controller.breakdownShares == pytest.approx([12.5, 3.2])

    def test_rerun_clears_previous_error(self, qapp):
        container = _make_container(raises=ValueError("gecici"))
        controller = SimulationController(container)
        controller.setTickersText("AKBNK")
        controller.runSimulation()
        assert controller.hasResult is False

        container.dca_backtest_service.run.side_effect = None
        container.dca_backtest_service.run.return_value = _result()
        controller.runSimulation()

        assert controller.hasResult is True
        assert controller.errorMessage == ""


class TestRangeToStartDate:
    def test_max_range_passes_far_past_start_date(self, qapp):
        container = _make_container()
        controller = SimulationController(container)
        controller.setTickersText("AKBNK")
        controller.setSelectedRangeKey("MAX")

        controller.runSimulation()

        call = container.dca_backtest_service.run.call_args
        assert call.kwargs["start_date"].year <= 2000

    def test_1y_range_passes_roughly_one_year_back(self, qapp):
        container = _make_container()
        controller = SimulationController(container)
        controller.setTickersText("AKBNK")
        controller.setSelectedRangeKey("1Y")

        controller.runSimulation()

        call = container.dca_backtest_service.run.call_args
        days_back = (date.today() - call.kwargs["start_date"]).days
        assert 360 <= days_back <= 370

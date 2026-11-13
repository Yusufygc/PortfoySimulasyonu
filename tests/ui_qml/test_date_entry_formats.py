"""Elle girilen tarih her alanda GG.AA.YYYY ile kabul edilir (eski YYYY-AA-GG de). 2026-11-14: tarihi 11 ayrı yer ayrıştırıyordu."""
from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

import pytest

from src.ui_qml.controllers import planning_controller as planning_module
from src.ui_qml.controllers.model_portfolio_controller import ModelPortfolioController
from src.ui_qml.controllers.planning_controller import PlanningController
from src.ui_qml.controllers.stock_detail_controller import parse_trade_moment


@pytest.mark.parametrize("text", ["05.01.2026", "2026-01-05"])
def test_trade_order_date_accepts_turkish_and_legacy_format(text):
    assert parse_trade_moment(text, "14:30") == (dt.date(2026, 1, 5), dt.time(14, 30))


def test_trade_order_date_error_names_the_turkish_format():
    with pytest.raises(ValueError, match="GG.AA.YYYY"):
        parse_trade_moment("05/01/2026", "")


class _GoalService:
    def __init__(self):
        self.calls = []

    def add_goal(self, name, target, deadline, priority):
        self.calls.append(("add", name, deadline))

    def update_goal(self, goal_id, name, target, deadline, priority):
        self.calls.append(("update", name, deadline))

    def get_all_goals(self):
        return []


def _planning(qapp):
    ctrl = PlanningController(container=SimpleNamespace())
    ctrl._service = _GoalService()
    ctrl.loadGoals = lambda: None
    return ctrl


@pytest.mark.parametrize("text", ["31.12.2027", "2027-12-31"])
def test_goal_deadline_accepts_turkish_and_legacy_format(qapp, text):
    ctrl = _planning(qapp)
    ctrl.addGoal("hedef", 1000.0, text, "ORTA")
    ctrl.updateGoal(1, "hedef", 1000.0, text, "ORTA")
    assert ctrl._service.calls == [("add", "hedef", dt.date(2027, 12, 31)), ("update", "hedef", dt.date(2027, 12, 31))]


def test_goal_deadline_invalid_text_reports_the_turkish_format(qapp):
    ctrl = _planning(qapp)
    results = []
    ctrl.operationResult.connect(lambda ok, message: results.append((ok, message)))
    ctrl.addGoal("hedef", 1000.0, "yarın", "ORTA")
    assert ctrl._service.calls == [] and results and results[0][0] is False and "GG.AA.YYYY" in results[0][1]


def test_dca_dates_accept_turkish_format(qapp, monkeypatch):
    ctrl = PlanningController(container=SimpleNamespace())
    ctrl._dca_service = object()
    captured = []
    ctrl._execute_dca = lambda tickers, amount, start, end: captured.append((start, end))
    monkeypatch.setattr(planning_module, "run_later", lambda owner, ms, work: work())
    ctrl.runDcaBacktest("THYAO", 1000.0, "01.02.2024", "2025-03-04")
    assert captured == [(dt.date(2024, 2, 1), dt.date(2025, 3, 4))]


class _ModelService:
    def __init__(self):
        self.trades, self.moves = [], []

    def add_trade_by_ticker(self, portfolio_id, ticker, trade_input):
        self.trades.append(trade_input.trade_date)

    def add_capital_movement(self, spec):
        self.moves.append(spec.movement_date)


def _model_controller(qapp):
    names = {name: None for name in ModelPortfolioController.REQUIRES}
    ctrl = ModelPortfolioController(container=SimpleNamespace(**names))
    ctrl._service = _ModelService()
    ctrl._current_portfolio_id = 1
    ctrl.refreshData = lambda: None
    return ctrl


@pytest.mark.parametrize("text", ["06.03.2026", "2026-03-06"])
def test_model_portfolio_trade_and_capital_accept_turkish_and_legacy_format(qapp, text):
    ctrl = _model_controller(qapp)
    ctrl.addTrade("THYAO", "BUY", 10, 100.0, text, "10:00")
    ctrl.addCapitalMovement("DEPOSIT", 500.0, text, "10:00", "")
    assert ctrl._service.trades == [dt.date(2026, 3, 6)] and ctrl._service.moves == [dt.date(2026, 3, 6)]


def test_model_portfolio_invalid_date_reports_the_turkish_format(qapp):
    ctrl = _model_controller(qapp)
    results = []
    ctrl.operationResult.connect(lambda ok, message: results.append((ok, message)))
    ctrl.addTrade("THYAO", "BUY", 10, 100.0, "yarın", "10:00")
    assert ctrl._service.trades == [] and results and results[0][0] is False and "GG.AA.YYYY" in results[0][1]


@pytest.mark.parametrize("time_text", ["25:99", "10.30", "abc"])
def test_model_portfolio_invalid_time_reports_the_hh_mm_format(qapp, time_text):
    ctrl = _model_controller(qapp)
    results = []
    ctrl.operationResult.connect(lambda ok, message: results.append((ok, message)))
    ctrl.addTrade("THYAO", "BUY", 10, 100.0, "06.03.2026", time_text)
    ctrl.addCapitalMovement("DEPOSIT", 500.0, "06.03.2026", time_text, "")
    assert ctrl._service.trades == [] and ctrl._service.moves == []
    assert len(results) == 2 and all(ok is False and "SS:DD" in message for ok, message in results)

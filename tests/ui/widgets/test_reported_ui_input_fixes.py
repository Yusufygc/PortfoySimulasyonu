from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6")
from src.qt_compat.qtcore import QDate
from src.qt_compat.qtwidgets import QDialog, QMessageBox, QPushButton

from src.application.services.planning.planning_service import PlanningService
from src.domain.models.financial_goal import FinancialGoal, GoalStatus
from src.ui.widgets.dashboard.dialogs.capital_dialog import CapitalDialog
from src.ui.widgets.model_portfolio.dialogs.capital_movement_dialog import CapitalMovementDialog
from src.ui.widgets.dashboard.dialogs.new_stock_trade_dialog import NewStockTradeDialog
from src.ui.widgets.planning.dialogs.contribution_dialog import ContributionDialog
from src.ui.widgets.planning.dialogs.goal_input_dialog import GoalInputDialog
from src.ui.widgets.planning.panels.budget_form_panel import BudgetFormPanel
from src.ui.widgets.planning.panels.budget_item_row import BudgetItemRow
from src.ui.widgets.planning.panels.goals_panel import GoalsPanel
from src.ui.widgets.shared import CurrencySpinBox
from src.ui.widgets.watchlist.dialogs.add_stock_to_watchlist_dialog import AddStockToWatchlistDialog


class _FakeThreadPool:
    def __init__(self):
        self.started = []

    def start(self, worker):
        self.started.append(worker)


@pytest.mark.parametrize("ticker", ["+", "12345", "ASELS+"])
def test_new_stock_trade_dialog_rejects_invalid_ticker_before_lookup(qapp, monkeypatch, ticker):
    warnings = []
    pool = _FakeThreadPool()
    lookup_calls = []

    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args))
    monkeypatch.setattr(
        "src.ui.widgets.dashboard.dialogs.new_stock_trade_dialog.QThreadPool.globalInstance",
        staticmethod(lambda: pool),
    )

    dialog = NewStockTradeDialog(price_lookup_func=lambda symbol: lookup_calls.append(symbol))
    dialog.line_ticker.setText(ticker)

    dialog._on_ticker_edited()

    assert warnings
    assert lookup_calls == []
    assert pool.started == []


def test_new_stock_trade_dialog_allows_real_alphanumeric_bist_ticker(qapp, monkeypatch):
    pool = _FakeThreadPool()
    warnings = []

    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args))
    monkeypatch.setattr(
        "src.ui.widgets.dashboard.dialogs.new_stock_trade_dialog.QThreadPool.globalInstance",
        staticmethod(lambda: pool),
    )

    dialog = NewStockTradeDialog(price_lookup_func=lambda symbol: None)
    dialog.line_ticker.setText("A1CAP")

    dialog._on_ticker_edited()

    assert warnings == []
    assert len(pool.started) == 1
    assert dialog._last_lookup_ticker == "A1CAP.IS"


@pytest.mark.parametrize("ticker", ["12345", "ASELS+"])
def test_watchlist_add_stock_dialog_rejects_invalid_ticker(qapp, monkeypatch, ticker):
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args))

    dialog = AddStockToWatchlistDialog()
    dialog.ticker_edit.setText(ticker)

    dialog._on_accept_clicked()

    assert warnings
    assert dialog.result() != QDialog.Accepted


def test_watchlist_add_stock_dialog_accepts_alphanumeric_ticker(qapp, monkeypatch):
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args))

    dialog = AddStockToWatchlistDialog()
    dialog.ticker_edit.setText("A1CAP")

    dialog._on_accept_clicked()

    assert warnings == []
    assert dialog.result() == QDialog.Accepted


@pytest.mark.parametrize("raw_text", ["abc", "-15"])
def test_currency_spin_box_exposes_invalid_user_input_without_minimum_fallback(qapp, raw_text):
    box = CurrencySpinBox()
    box.setRange(0.01, 10_000_000)
    box.setDecimals(2)
    box.setSuffix(" TL")
    box.setValue(123.45)

    box.lineEdit().setText(raw_text)

    assert box.has_valid_input(require_positive=True) is False
    assert box.valueFromText(raw_text) != pytest.approx(box.minimum())


@pytest.mark.parametrize("dialog_factory", [lambda: CapitalDialog(Decimal("1000")), lambda: ContributionDialog("Ev")])
@pytest.mark.parametrize("raw_text", ["-1000", "-", "abc", "100abc"])
def test_amount_dialogs_reject_negative_and_text_amounts(qapp, monkeypatch, dialog_factory, raw_text):
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args))

    dialog = dialog_factory()
    dialog.spin_amount.lineEdit().setText(raw_text)

    dialog.accept()

    assert warnings
    assert dialog.result() != QDialog.Accepted
    if isinstance(dialog, CapitalDialog):
        assert dialog.get_result() is None
    else:
        assert dialog.get_amount() == 0.0


@pytest.mark.parametrize("raw_text", ["-1000", "-", "abc", "100abc"])
def test_model_capital_movement_dialog_rejects_invalid_amounts(qapp, monkeypatch, raw_text):
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args))

    dialog = CapitalMovementDialog(Decimal("1000"), Decimal("1000"))
    dialog.spin_amount.lineEdit().setText(raw_text)

    dialog.accept()

    assert warnings
    assert dialog.result() != QDialog.Accepted
    assert dialog.get_result() is None


def test_capital_dialog_rejects_negative_after_focus_out_clamp(qapp, monkeypatch):
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args))

    dialog = CapitalDialog(Decimal("1000"))
    dialog.spin_amount.setFocus()
    qapp.processEvents()
    dialog.spin_amount.lineEdit().setText("-1000")
    dialog.spin_amount._remember_user_text("-1000")
    dialog.spin_amount.clearFocus()
    qapp.processEvents()

    dialog.accept()

    assert warnings
    assert dialog.result() != QDialog.Accepted
    assert dialog.get_result() is None


def test_goal_input_dialog_warns_for_blank_name_and_rejects_today(qapp, monkeypatch):
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args))

    dialog = GoalInputDialog()
    dialog.txt_name.setText("")
    dialog.accept()

    assert warnings
    assert dialog.result() != QDialog.Accepted
    assert dialog.date_deadline.minimumDate() == QDate.currentDate()

    warnings.clear()
    dialog.txt_name.setText("Ev")
    dialog.date_deadline.setDate(QDate.currentDate())

    dialog.accept()

    assert warnings
    assert dialog.result() != QDialog.Accepted
    assert dialog.get_result() is None


def test_goal_input_dialog_accepts_tomorrow(qapp, monkeypatch):
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args))

    dialog = GoalInputDialog()
    dialog.txt_name.setText("Ev")
    dialog.date_deadline.setDate(QDate.currentDate().addDays(1))

    dialog.accept()

    assert warnings == []
    assert dialog.result() == QDialog.Accepted


def test_budget_item_row_accepts_one_billion_without_ten_million_clamp(qapp):
    row = BudgetItemRow("Maas", 0)

    row.amount_spin.lineEdit().setText("1000000000")

    assert row.amount_spin.maximum() == 1_000_000_000
    assert row.amount_spin.has_valid_input() is True
    assert row.get_amount() == pytest.approx(1_000_000_000)


def test_budget_form_panel_target_accepts_one_billion_without_ten_million_clamp(qapp):
    panel = BudgetFormPanel()

    panel.spin_target.lineEdit().setText("1000000000")
    budget = panel.get_budget("2026-06")

    assert panel.spin_target.maximum() == 1_000_000_000
    assert panel.spin_target.has_valid_input() is True
    assert budget.savings_target == pytest.approx(1_000_000_000)


def test_budget_amount_above_one_billion_is_not_silently_clamped(qapp):
    row = BudgetItemRow("Bonus", 123)

    row.amount_spin.lineEdit().setText("1000000001")

    assert row.amount_spin.has_valid_input() is False
    assert row.get_amount() == pytest.approx(123)
    assert row.amount_spin.valueFromText("1000000001") != pytest.approx(1_000_000_000)


def test_goals_panel_sorts_by_priority_and_months_and_disables_completed_contribution(qapp):
    goals = [
        FinancialGoal(id=1, name="Low", target_amount=Decimal("1000"), deadline=date.today() + timedelta(days=120), priority="LOW"),
        FinancialGoal(id=2, name="High Later", target_amount=Decimal("1000"), deadline=date.today() + timedelta(days=240), priority="HIGH"),
        FinancialGoal(id=3, name="High Soon", target_amount=Decimal("1000"), deadline=date.today() + timedelta(days=60), priority="HIGH"),
        FinancialGoal(
            id=4,
            name="Done",
            target_amount=Decimal("1000"),
            current_amount=Decimal("1000"),
            deadline=date.today() + timedelta(days=30),
            priority="MEDIUM",
            status=GoalStatus.COMPLETED,
        ),
    ]
    panel = GoalsPanel()

    panel.load(goals)

    assert [panel._table.item(row, 0).text() for row in range(panel._table.rowCount())] == [
        "High Soon",
        "High Later",
        "Done",
        "Low",
    ]
    done_actions = panel._table.cellWidget(2, 7)
    contrib_button = done_actions.findChildren(QPushButton)[1]
    assert contrib_button.isEnabled() is False


class _PlanningRepo:
    def __init__(self, goal):
        self.goal = goal
        self.updated = None

    def get_goal_by_id(self, goal_id):
        return self.goal if self.goal.id == goal_id else None

    def update_goal(self, goal):
        self.updated = goal


def test_planning_service_rejects_contribution_to_completed_goal():
    goal = FinancialGoal(
        id=1,
        name="Done",
        target_amount=Decimal("1000"),
        current_amount=Decimal("1000"),
        status=GoalStatus.COMPLETED,
    )
    repo = _PlanningRepo(goal)
    service = PlanningService(repo)

    with pytest.raises(ValueError, match="Tamamlanan hedefe katk"):
        service.add_contribution(1, 10)

    assert repo.updated is None

from __future__ import annotations

from datetime import datetime, timezone
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import threading

import pytest

pytest.importorskip("PySide6")
from src.qt_compat.qtcore import Qt
from src.qt_compat.qttest import QTest
from src.qt_compat.qtwidgets import QDialog, QMessageBox

from src.domain.models.corporate_action import ActionType
from src.domain.models.corporate_action_candidate import CorporateActionCandidate, CorporateActionCandidateStatus
from src.domain.models.stock import Stock
from src.ui.pages.settings.corporate_action_candidates_panel import CorporateActionCandidateEditDialog
from src.ui.widgets.dashboard.dialogs.capital_dialog import CapitalDialog
from src.ui.widgets.dashboard.dialogs.corporate_action_dialog import CorporateActionDialog, CorporateActionDialogContext
from src.ui.widgets.dashboard.dialogs.date_range_dialog import DateRangeDialog
from src.ui.widgets.dashboard.dialogs.new_stock_trade_dialog import NewStockTradeDialog
from src.ui.widgets.model_portfolio.dialogs.portfolio_input_dialog import PortfolioInputDialog
from src.ui.widgets.model_portfolio.dialogs.trade_input_dialog import TradeInputDialog
from src.ui.widgets.planning.dialogs.contribution_dialog import ContributionDialog
from src.ui.widgets.planning.dialogs.goal_input_dialog import GoalInputDialog
from src.ui.widgets.stock.dialogs.edit_stock_dialog import EditStockDialog
from src.ui.widgets.stock.dialogs.trade_dialog import TradeDialog
from src.ui.widgets.watchlist.dialogs.add_stock_to_watchlist_dialog import AddStockToWatchlistDialog
from src.ui.widgets.watchlist.dialogs.watchlist_dialog import WatchlistDialog


def test_model_trade_dialog_shows_readonly_amount_and_keeps_result_shape(qapp):
    dialog = TradeInputDialog("BUY", price_lookup_func=None)

    dialog.spin_qty.setValue(100)
    dialog.spin_price.setValue(12.34)

    assert dialog.edit_amount.isReadOnly()
    assert dialog.edit_amount.text() == "1,234.00 TL"

    dialog.spin_qty.setValue(3)

    assert dialog.edit_amount.text() == "37.02 TL"

    dialog.txt_ticker.setText("ASELS")
    dialog.accept()
    result = dialog.get_result()

    assert set(result) == {"ticker", "quantity", "price", "trade_date", "trade_time", "side"}
    assert result["ticker"] == "ASELS"
    assert result["quantity"] == 3
    assert result["price"] == Decimal("12.34")


def test_model_trade_dialog_lookup_updates_amount_and_enter_preserves_lookup(qapp):
    calls = []

    def lookup(ticker):
        calls.append(ticker)
        return SimpleNamespace(price=Decimal("12.34"))

    dialog = TradeInputDialog("BUY", price_lookup_func=lookup)
    dialog.txt_ticker.setText("ASELS")
    dialog.txt_ticker.setFocus()
    dialog.show()
    qapp.processEvents()

    QTest.keyClick(dialog.txt_ticker, Qt.Key_Return)
    qapp.processEvents()

    assert calls == ["ASELS"]
    assert dialog.result() == 0
    assert dialog.edit_amount.text() == "1,234.00 TL"


def test_dashboard_trade_wizard_enter_moves_forward_then_accepts(qapp):
    dialog = NewStockTradeDialog(price_lookup_func=None)
    dialog.line_ticker.setText("ASELS")
    dialog.current_price = Decimal("10.00")
    dialog.fetched_stock_name = "ASELSAN"
    dialog.line_ticker.setFocus()
    dialog.show()
    qapp.processEvents()

    QTest.keyClick(dialog.line_ticker, Qt.Key_Return)
    qapp.processEvents()

    assert dialog.stack.currentIndex() == 1
    assert dialog.result() == 0

    dialog.spin_quantity.setFocus()
    QTest.keyClick(dialog.spin_quantity, Qt.Key_Return)
    qapp.processEvents()

    assert dialog.result() == QDialog.Accepted


def test_dashboard_trade_wizard_enter_waits_for_lookup_before_advancing(qapp, monkeypatch):
    lookup_started = threading.Event()
    release_lookup = threading.Event()
    prompts = []

    def lookup(_ticker):
        lookup_started.set()
        release_lookup.wait(timeout=1)
        return SimpleNamespace(
            price=Decimal("12.34"),
            source="intraday",
            company_name="ASELSAN",
            normalized_ticker="ASELS.IS",
            as_of=datetime(2026, 6, 5, tzinfo=timezone.utc),
        )

    def fake_question(*args, **kwargs):
        prompts.append((args, kwargs))
        return QMessageBox.No

    monkeypatch.setattr(QMessageBox, "question", fake_question)

    dialog = NewStockTradeDialog(price_lookup_func=lookup)
    dialog.line_ticker.setText("ASELS")
    dialog.line_ticker.setFocus()
    dialog.show()
    qapp.processEvents()

    QTest.keyClick(dialog.line_ticker, Qt.Key_Return)

    for _ in range(20):
        qapp.processEvents()
        if lookup_started.is_set():
            break

    assert lookup_started.is_set()
    assert dialog.stack.currentIndex() == 0
    assert dialog.result() == 0
    assert dialog.btn_next.isEnabled() is False
    assert dialog._price_lookup_in_flight is True
    assert prompts == []

    release_lookup.set()
    for _ in range(50):
        qapp.processEvents()
        if dialog.current_price == Decimal("12.34"):
            break

    assert dialog.current_price == Decimal("12.34")
    assert dialog._price_lookup_in_flight is False
    assert dialog.btn_next.isEnabled() is True
    assert prompts == []

    QTest.keyClick(dialog.line_ticker, Qt.Key_Return)
    qapp.processEvents()

    assert dialog.stack.currentIndex() == 1


def test_custom_dialogs_hide_context_help_button(qapp):
    candidate = CorporateActionCandidate(
        id=1,
        ticker="ASELS.IS",
        stock_id=1,
        source="KAP",
        source_disclosure_id="1",
        source_url=None,
        action_type=ActionType.BEDELSIZ,
        status=CorporateActionCandidateStatus.READY,
        ratio=Decimal("0.5"),
        subscription_price=None,
        announcement_date=None,
        ex_date=date(2026, 6, 2),
        confidence=Decimal("0.9"),
    )
    dialogs = [
        TradeInputDialog("BUY"),
        NewStockTradeDialog(price_lookup_func=None),
        CapitalDialog(Decimal("1000")),
        CorporateActionDialog(CorporateActionDialogContext("ASELS.IS", 1, 100, Decimal("10"), Decimal("1000"), Decimal("20"))),
        DateRangeDialog(),
        PortfolioInputDialog(),
        GoalInputDialog(),
        ContributionDialog("Hedef"),
        WatchlistDialog("Liste"),
        AddStockToWatchlistDialog(),
        EditStockDialog(Stock(id=1, ticker="ASELS.IS", name="ASELS", currency_code="TRY")),
        TradeDialog(stock_id=1, ticker="ASELS.IS", price_lookup_func=None),
        CorporateActionCandidateEditDialog(candidate, stock_repo=None),
    ]

    offenders = [type(dialog).__name__ for dialog in dialogs if dialog.windowFlags() & Qt.WindowContextHelpButtonHint]

    assert offenders == []


def test_custom_dialogs_keep_close_button_enabled(qapp):
    candidate = CorporateActionCandidate(
        id=1,
        ticker="ASELS.IS",
        stock_id=1,
        source="KAP",
        source_disclosure_id="1",
        source_url=None,
        action_type=ActionType.BEDELSIZ,
        status=CorporateActionCandidateStatus.READY,
        ratio=Decimal("0.5"),
        subscription_price=None,
        announcement_date=None,
        ex_date=date(2026, 6, 2),
        confidence=Decimal("0.9"),
    )
    dialogs = [
        TradeInputDialog("BUY"),
        NewStockTradeDialog(price_lookup_func=None),
        CapitalDialog(Decimal("1000")),
        CorporateActionDialog(CorporateActionDialogContext("ASELS.IS", 1, 100, Decimal("10"), Decimal("1000"), Decimal("20"))),
        DateRangeDialog(),
        PortfolioInputDialog(),
        GoalInputDialog(),
        ContributionDialog("Hedef"),
        WatchlistDialog("Liste"),
        AddStockToWatchlistDialog(),
        EditStockDialog(Stock(id=1, ticker="ASELS.IS", name="ASELS", currency_code="TRY")),
        TradeDialog(stock_id=1, ticker="ASELS.IS", price_lookup_func=None),
        CorporateActionCandidateEditDialog(candidate, stock_repo=None),
    ]

    offenders = [type(dialog).__name__ for dialog in dialogs if not dialog.windowFlags() & Qt.WindowCloseButtonHint]

    assert offenders == []


def test_enter_triggers_primary_actions_for_representative_dialogs(qapp):
    capital = CapitalDialog(Decimal("1000"))
    capital.spin_amount.setFocus()
    capital.show()
    qapp.processEvents()

    QTest.keyClick(capital.spin_amount, Qt.Key_Return)
    qapp.processEvents()

    portfolio = PortfolioInputDialog()
    portfolio.txt_name.setText("Deneme")
    portfolio.txt_name.setFocus()
    portfolio.show()
    qapp.processEvents()

    QTest.keyClick(portfolio.txt_name, Qt.Key_Return)
    qapp.processEvents()

    assert capital.result() == QDialog.Accepted
    assert portfolio.result() == QDialog.Accepted


def test_watchlist_dialog_validation_prevents_empty_name(qapp, monkeypatch):
    dialog = WatchlistDialog("Liste")
    dialog.name_input.setText("")

    warnings = []
    monkeypatch.setattr("src.ui.widgets.shared.feedback.toast.Toast.warning", lambda parent, msg: warnings.append(msg))

    dialog.accept()
    assert dialog.result() != QDialog.Accepted
    assert len(warnings) == 1
    assert "boş olamaz" in warnings[0].lower()

    dialog.name_input.setText("Yeni Liste")
    dialog.accept()
    assert dialog.result() == QDialog.Accepted

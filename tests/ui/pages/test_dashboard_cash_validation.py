import sys
from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6")
from src.qt_compat.qtwidgets import QApplication, QDialog

from src.ui.pages.dashboard.dashboard_actions import DashboardActions
from src.ui.pages.dashboard.dashboard_summary_cards import DashboardSummaryCards


app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class AcceptedCapitalDialog:
    def __init__(self, *_args, **_kwargs):
        pass

    def exec(self):
        return QDialog.Accepted

    def get_result(self):
        return {
            "action": "deposit",
            "amount": Decimal("1000"),
            "movement_date": None,
            "movement_time": None,
            "notes": None
        }


class InvalidCapitalDialog:
    def __init__(self, *_args, **_kwargs):
        pass

    def exec(self):
        return QDialog.Accepted

    def get_result(self):
        return None


def test_dashboard_capital_management_writes_cash_movement(monkeypatch):
    calls = []
    presenter = SimpleNamespace(load_capital=lambda: calls.append("load"), refresh_data=lambda: calls.append("refresh"))
    cash_service = SimpleNamespace(add_deposit=lambda amount, movement_date=None, movement_time=None, notes=None: calls.append(("deposit", amount, movement_date, movement_time, notes)))
    page = SimpleNamespace(_capital=Decimal("0"), capital_dialog_cls=AcceptedCapitalDialog, cash_movement_service=cash_service)
    monkeypatch.setattr("src.ui.pages.dashboard.dashboard_actions.QMessageBox.information", lambda *args, **kwargs: None)

    DashboardActions(page, presenter).on_capital_management()

    assert calls == [("deposit", Decimal("1000"), None, None, "Sermaye ekleme"), "load", "refresh"]


def test_dashboard_capital_management_ignores_invalid_dialog_result():
    calls = []
    presenter = SimpleNamespace(load_capital=lambda: calls.append("load"), refresh_data=lambda: calls.append("refresh"))
    cash_service = SimpleNamespace(
        add_deposit=lambda *args, **kwargs: calls.append(("deposit", args, kwargs)),
        add_withdraw=lambda *args, **kwargs: calls.append(("withdraw", args, kwargs)),
    )
    page = SimpleNamespace(_capital=Decimal("0"), capital_dialog_cls=InvalidCapitalDialog, cash_movement_service=cash_service)

    DashboardActions(page, presenter).on_capital_management()

    assert calls == []


def test_dashboard_capital_management_passes_service_validation_warning(monkeypatch):
    warnings = []
    presenter = SimpleNamespace(load_capital=lambda: None, refresh_data=lambda: None)
    cash_service = SimpleNamespace(
        add_deposit=lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("Tutar pozitif olmalıdır.")),
    )
    page = SimpleNamespace(_capital=Decimal("0"), capital_dialog_cls=AcceptedCapitalDialog, cash_movement_service=cash_service)
    monkeypatch.setattr("src.ui.pages.dashboard.dashboard_actions.QMessageBox.warning", lambda *args, **kwargs: warnings.append(args[2]))

    DashboardActions(page, presenter).on_capital_management()

    assert warnings == ["Tutar pozitif olmalıdır."]


def test_dashboard_new_trade_shows_warning_for_invalid_trade(monkeypatch):
    warnings = []
    presenter = SimpleNamespace(load_capital=lambda: None, refresh_data=lambda: None)
    trade_service = SimpleNamespace(
        submit_trade=lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("Yetersiz nakit"))
    )
    dialog = SimpleNamespace(
        get_result=lambda: {
            "ticker": "ASELS",
            "name": "ASELS",
            "side": "BUY",
            "quantity": 10,
            "price": Decimal("10"),
            "trade_date": None,
            "trade_time": None,
        },
    )
    setattr(dialog, "exec", lambda: QDialog.Accepted)
    page = SimpleNamespace(
        new_trade_dialog_cls=lambda **kwargs: dialog,
        price_lookup_func=None,
        trade_entry_service=trade_service,
        _last_trade_result=None,
    )
    monkeypatch.setattr(
        "src.ui.pages.dashboard.dashboard_actions.QMessageBox.warning",
        lambda *args, **kwargs: warnings.append(args[2]),
    )

    DashboardActions(page, presenter).on_new_trade()

    assert warnings == ["Yetersiz nakit"]


def test_dashboard_new_trade_blocks_closed_market_session(monkeypatch):
    warnings = []
    submit_calls = []
    presenter = SimpleNamespace(load_capital=lambda: None, refresh_data=lambda: None)
    trade_service = SimpleNamespace(submit_trade=lambda **kwargs: submit_calls.append(kwargs))
    dialog = SimpleNamespace(
        get_result=lambda: {
            "ticker": "ASELS",
            "name": "ASELS",
            "side": "BUY",
            "quantity": 10,
            "price": Decimal("10"),
            "trade_date": date(2026, 6, 6),
            "trade_time": time(11, 0),
        },
    )
    setattr(dialog, "exec", lambda: QDialog.Accepted)
    market_session_service = SimpleNamespace(
        status_for=lambda trade_date, trade_time=None: SimpleNamespace(
            is_open=False,
            message="Kapali seans",
        )
    )
    page = SimpleNamespace(
        new_trade_dialog_cls=lambda **kwargs: dialog,
        price_lookup_func=None,
        trade_entry_service=trade_service,
        market_session_service=market_session_service,
        _last_trade_result=None,
    )
    monkeypatch.setattr(
        "src.ui.pages.dashboard.dashboard_actions.QMessageBox.warning",
        lambda *args, **kwargs: warnings.append(args[2]),
    )

    DashboardActions(page, presenter).on_new_trade()

    assert submit_calls == []
    assert warnings
    assert "BIST" in warnings[0]


def test_dashboard_cash_card_never_displays_negative_cash():
    cards = DashboardSummaryCards()

    cards.update_base_metrics(
        total_value=Decimal("0"),
        total_cost=Decimal("0"),
        capital=Decimal("-759198.88"),
        profit_loss=Decimal("0"),
    )

    assert cards.lbl_capital.text() == "₺ 0.00"
    assert cards.lbl_capital.property("state") == "neutral"

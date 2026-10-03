"""DividendController (nakit temettü kaydı) ve DividendDialog.qml."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Q_ARG, QMetaObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from src.application.services.portfolio.cash_movement_service import CashMovementService
from src.domain.models.cash_movement import CashMovement
from src.ui_qml.controllers.dividend_controller import DividendController, parse_amount, parse_date

QML_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"


@pytest.fixture(scope="module")
def qapp():
    return QGuiApplication.instance() or QGuiApplication([])


class FakeRepo:
    def __init__(self):
        self.movements = []

    def insert_movement(self, movement):
        saved = CashMovement(
            id=len(self.movements) + 1, movement_date=movement.movement_date, movement_time=None,
            type=movement.type, amount=movement.amount, notes=movement.notes, stock_id=movement.stock_id,
        )
        self.movements.append(saved)
        return saved

    def get_movements_by_type(self, movement_type, stock_id=None):
        return [m for m in self.movements if m.type == movement_type and (stock_id is None or m.stock_id == stock_id)]

    def get_movement(self, movement_id):
        return next((m for m in self.movements if m.id == movement_id), None)

    def delete_movement(self, movement_id):
        self.movements = [m for m in self.movements if m.id != movement_id]


def _controller(held_quantity: int = 10):
    portfolio_service = MagicMock()
    portfolio_service.get_position_quantity_as_of.return_value = held_quantity
    repo = FakeRepo()
    container = SimpleNamespace(
        cash_movement_service=CashMovementService(repo, portfolio_service),
        stock_lookup_service=SimpleNamespace(find_stock=lambda ticker: SimpleNamespace(id=1, ticker=ticker)),
    )
    return DividendController(container=container), repo, portfolio_service


def _capture(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


class TestParsing:
    @pytest.mark.parametrize(
        "text,expected",
        [("1234.56", "1234.56"), ("1.234,56", "1234.56"), ("25,5", "25.5"), (" 100 ", "100")],
    )
    def test_parse_amount_accepts_turkish_and_plain_formats(self, text, expected):
        assert parse_amount(text) == Decimal(expected)

    @pytest.mark.parametrize("text", ["", "abc", "0", "-5", "nan", "inf"])
    def test_parse_amount_rejects_invalid_or_non_positive(self, text):
        assert parse_amount(text) is None

    def test_parse_date_accepts_iso_and_turkish(self):
        assert parse_date("2026-03-02") == date(2026, 3, 2)
        assert parse_date("02.03.2026") == date(2026, 3, 2)
        assert parse_date("yarın") is None


class TestDividendController:
    def test_add_dividend_updates_list_total_and_notifies(self, qapp):
        ctrl, repo, _ = _controller()
        ctrl.loadFor("THYAO.IS")
        notifications, portfolio_changed = _capture(ctrl.notification), _capture(ctrl.portfolioChanged)

        ctrl.addDividend("1.250,50", "2026-03-02", "")

        assert notifications == [(True, "1.250,50 ₺ temettü nakit bakiyeye eklendi.")]
        assert len(portfolio_changed) == 1
        assert ctrl.ticker == "THYAO"
        assert ctrl.hasDividends is True
        assert ctrl.totalText == "1.250,50 ₺"
        assert ctrl.dividends == [
            {"id": 1, "dateText": "02.03.2026", "amountText": "1.250,50 ₺", "note": "THYAO temettü"}
        ]
        assert repo.movements[0].stock_id == 1 and repo.movements[0].amount == Decimal("1250.50")

    def test_newest_dividend_is_listed_first(self, qapp):
        ctrl, _, _ = _controller()
        ctrl.loadFor("THYAO")
        ctrl.addDividend("10", "2026-01-10", "ilk")
        ctrl.addDividend("20", "2026-03-10", "ikinci")

        assert [row["note"] for row in ctrl.dividends] == ["ikinci", "ilk"]
        assert ctrl.totalText == "30,00 ₺"

    def test_invalid_amount_is_rejected_without_saving(self, qapp):
        ctrl, repo, _ = _controller()
        ctrl.loadFor("THYAO")
        notifications = _capture(ctrl.notification)

        ctrl.addDividend("abc", "2026-03-02", "")

        assert notifications[0][0] is False and "Tutar" in notifications[0][1]
        assert repo.movements == []

    def test_invalid_date_is_rejected_without_saving(self, qapp):
        ctrl, repo, _ = _controller()
        ctrl.loadFor("THYAO")
        notifications = _capture(ctrl.notification)

        ctrl.addDividend("10", "dün", "")

        assert notifications[0][0] is False and "Tarih" in notifications[0][1]
        assert repo.movements == []

    def test_service_validation_message_reaches_user(self, qapp):
        ctrl, repo, _ = _controller(held_quantity=0)
        ctrl.loadFor("THYAO")
        notifications, portfolio_changed = _capture(ctrl.notification), _capture(ctrl.portfolioChanged)

        ctrl.addDividend("10", "2026-03-02", "")

        assert notifications == [(False, "Bu tarihte hissenin portföyde pozisyonu yoktu; temettü kaydedilemez.")]
        assert portfolio_changed == [] and repo.movements == []

    def test_unknown_ticker_cannot_save(self, qapp):
        ctrl, repo, _ = _controller()
        ctrl._container.stock_lookup_service = SimpleNamespace(find_stock=lambda ticker: None)
        ctrl.loadFor("YOKTUR")
        notifications = _capture(ctrl.notification)

        ctrl.addDividend("10", "2026-03-02", "")

        assert notifications[0][0] is False
        assert repo.movements == []

    def test_delete_dividend_removes_row_and_signals_portfolio_change(self, qapp):
        ctrl, repo, portfolio_service = _controller()
        ctrl.loadFor("THYAO")
        ctrl.addDividend("10", "2026-03-02", "")
        notifications, portfolio_changed = _capture(ctrl.notification), _capture(ctrl.portfolioChanged)

        ctrl.deleteDividend(1)

        assert notifications == [(True, "Temettü kaydı silindi.")]
        assert len(portfolio_changed) == 1
        assert ctrl.hasDividends is False and ctrl.totalText == "0,00 ₺"
        assert repo.movements == []
        portfolio_service.validate_cash_removal.assert_called_once_with(1)

    def test_delete_blocked_by_timeline_keeps_row(self, qapp):
        ctrl, repo, portfolio_service = _controller()
        ctrl.loadFor("THYAO")
        ctrl.addDividend("10", "2026-03-02", "")
        portfolio_service.validate_cash_removal.side_effect = ValueError("nakit yetersiz kalır")
        notifications = _capture(ctrl.notification)

        ctrl.deleteDividend(1)

        assert notifications == [(False, "nakit yetersiz kalır")]
        assert len(repo.movements) == 1

    def test_without_container_everything_is_inert(self, qapp):
        ctrl = DividendController(container=None)
        notifications = _capture(ctrl.notification)

        ctrl.loadFor("THYAO")
        ctrl.addDividend("10", "2026-03-02", "")
        ctrl.deleteDividend(1)

        assert ctrl.dividends == []
        assert [n[0] for n in notifications] == [False, False]


def _load(engine, relative_path):
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / relative_path)))
    if not component.isReady():
        pytest.fail("\n".join(err.toString() for err in component.errors()))
    return component


class TestDividendDialogQml:
    def test_dialog_compiles_without_controller(self, qapp):
        engine = QQmlApplicationEngine()
        engine.addImportPath(str(QML_DIR))
        warnings = []
        engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))

        component = _load(engine, "components/DividendDialog.qml")
        item = component.create()

        assert item is not None
        assert warnings == []

    def test_open_loads_dividends_for_ticker(self, qapp):
        ctrl, _, _ = _controller()
        ctrl.loadFor("THYAO")
        ctrl.addDividend("50", "2026-03-02", "Temettü")
        engine = QQmlApplicationEngine()
        engine.addImportPath(str(QML_DIR))
        warnings = []
        engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
        engine.rootContext().setContextProperty("dividendController", ctrl)
        component = _load(engine, "components/DividendDialog.qml")
        item = component.create()

        QMetaObject.invokeMethod(item, "open", Q_ARG("QVariant", "THYAO"))

        assert item.property("isOpen") is True
        assert item.property("ticker") == "THYAO"
        assert item.property("hasDividends") is True
        assert warnings == []

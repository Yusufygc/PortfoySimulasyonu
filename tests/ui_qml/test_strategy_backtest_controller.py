"""StrategyBacktestController (Planlama > Strateji Testi) ve PlanningStrategyTab.qml."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from PySide6.QtCore import QMetaObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtWebEngineQuick import QtWebEngineQuick
from PySide6.QtWidgets import QApplication

from src.application.services.simulation.strategy_backtest import (
    BacktestSetup,
    equal_weight_function,
    simulate_rebalancing,
    simulate_stop_take,
)
from src.ui_qml.controllers.strategy_backtest_controller import (
    StrategyBacktestController,
    parse_date,
    parse_number,
)

QML_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"
CAPITAL = Decimal("1000")
DAYS = [date(2026, 1, 1) + timedelta(days=i) for i in range(5)]


@pytest.fixture(scope="session")
def qapp():
    QtWebEngineQuick.initialize()
    return QApplication.instance() or QApplication([])


class ImmediateExecutor:
    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)


def _stop_take_result():
    series = {d: {"A": Decimal(p)} for d, p in zip(DAYS, (100, 95, 90, 70, 50))}
    return simulate_stop_take(series, BacktestSetup(["A"], CAPITAL, DAYS[0]), 10, None)


def _rebalance_result():
    rows = [(date(2026, 1, 2), 100, 100), (date(2026, 2, 2), 200, 100), (date(2026, 3, 2), 100, 100)]
    series = {d: {"A": Decimal(a), "B": Decimal(b)} for d, a, b in rows}
    return simulate_rebalancing(series, BacktestSetup(["A", "B"], CAPITAL, rows[0][0]), 1, equal_weight_function(["A", "B"]))


class FakeService:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []

    def _answer(self, name, args):
        self.calls.append((name, args))
        if self.error:
            raise self.error
        return self.result

    def run_rebalancing(self, *args):
        return self._answer("rebalancing", args)

    def run_stop_take(self, *args):
        return self._answer("stop_take", args)


def _controller(service):
    ctrl = StrategyBacktestController(container=type("C", (), {"strategy_backtest_service": service})())
    ctrl._executor = ImmediateExecutor()
    return ctrl


def _capture(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


class TestParsing:
    @pytest.mark.parametrize("text,expected", [("100000", 100000.0), ("1.234,5", 1234.5), ("0,1", 0.1), (" 12.5 ", 12.5)])
    def test_parse_number(self, text, expected):
        assert parse_number(text) == pytest.approx(expected)

    @pytest.mark.parametrize("text", ["", "abc", "nan", "inf"])
    def test_parse_number_rejects_invalid(self, text):
        assert parse_number(text) is None

    def test_parse_date(self):
        assert parse_date("2026-03-02") == date(2026, 3, 2)
        assert parse_date("02.03.2026") == date(2026, 3, 2)
        assert parse_date("x") is None


class TestRun:
    def test_stop_take_result_is_formatted_for_qml(self, qapp):
        service = FakeService(_stop_take_result())
        ctrl = _controller(service)
        notes = _capture(ctrl.notification)

        ctrl.runStopTake("A", "1000", "2026-01-01", "2026-01-05", "10", "", "0")

        assert service.calls[0][0] == "stop_take"
        assert ctrl.hasResult is True and ctrl.isRunning is False
        assert ctrl.strategyReturnText == "%-10,00"
        assert ctrl.baselineReturnText == "%-50,00"
        assert ctrl.differenceText == "%+40,00" and ctrl.differencePositive is True
        assert ctrl.strategyValueText == "900,00 ₺"
        assert "1 pozisyon çıkışı" in ctrl.summaryText
        assert ctrl.events == [
            {"dateText": "03.01.2026", "ticker": "A", "actionText": "Stop-loss", "action": "STOP_LOSS",
             "detail": "A: giriş fiyatına göre %-10.0"}
        ]
        assert "LineSeries" in ctrl.chartHtml and "Al ve tut" in ctrl.chartHtml
        assert notes[-1] == (True, "Strateji testi tamamlandı.")

    def test_rebalancing_passes_parameters_to_service(self, qapp):
        service = FakeService(_rebalance_result())
        ctrl = _controller(service)

        ctrl.runRebalancing("THYAO, ASELS", "50.000", "2026-01-01", "2026-06-30", 3, "markowitz", "0,1")

        name, args = service.calls[0]
        assert name == "rebalancing"
        setup, months, weighting = args
        assert setup.tickers == ["THYAO", "ASELS"]
        assert setup.initial_capital == Decimal("50000")  # "50.000" Türkçe binlik ayracı
        assert (setup.start_date, setup.end_date, months, weighting) == (date(2026, 1, 1), date(2026, 6, 30), 3, "markowitz")
        assert setup.commission_rate == pytest.approx(0.001)
        assert "2 dengeleme" in ctrl.summaryText
        assert [e["actionText"] for e in ctrl.events][:2] == ["Dengeleme", "Dengeleme"]

    def test_service_error_is_reported_and_clears_running(self, qapp):
        ctrl = _controller(FakeService(error=ValueError("Seçilen hisseler için fiyat verisi bulunamadı.")))
        notes, running = _capture(ctrl.notification), _capture(ctrl.runningChanged)

        ctrl.runRebalancing("A B", "1000", "2026-01-01", "2026-02-01", 3, "equal", "")

        assert notes == [(False, "Seçilen hisseler için fiyat verisi bulunamadı.")]
        assert ctrl.isRunning is False and ctrl.hasResult is False
        assert len(running) == 2  # çalıştı, bitti

    def test_unexpected_error_hides_details(self, qapp):
        ctrl = _controller(FakeService(error=RuntimeError("iç hata ayrıntısı")))
        notes = _capture(ctrl.notification)

        ctrl.runStopTake("A", "1000", "2026-01-01", "2026-02-01", "10", "", "")

        assert notes == [(False, "Simülasyon çalıştırılamadı.")]

    def test_empty_result_is_reported(self, qapp):
        empty = simulate_stop_take({}, BacktestSetup(["A"], CAPITAL, DAYS[0]), 10, None)
        ctrl = _controller(FakeService(empty))
        notes = _capture(ctrl.notification)

        ctrl.runStopTake("A", "1000", "2026-01-01", "2026-02-01", "10", "", "")

        assert notes[0][0] is False and "işlem günü yok" in notes[0][1]
        assert ctrl.hasResult is False

    @pytest.mark.parametrize(
        "args,message",
        [
            (("A", "abc", "2026-01-01", "2026-02-01", "10", "", ""), "sermayesi"),
            (("A", "0", "2026-01-01", "2026-02-01", "10", "", ""), "sermayesi"),
            (("A", "1000", "dün", "2026-02-01", "10", "", ""), "Tarih"),
            (("A", "1000", "2026-01-01", "2026-02-01", "", "", ""), "en az birini"),
        ],
    )
    def test_form_validation_never_reaches_service(self, qapp, args, message):
        service = FakeService(_stop_take_result())
        ctrl = _controller(service)
        notes = _capture(ctrl.notification)

        ctrl.runStopTake(*args)

        assert notes[0][0] is False and message in notes[0][1]
        assert service.calls == []

    def test_without_service_it_reports_unavailable(self, qapp):
        ctrl = StrategyBacktestController(container=None)
        notes = _capture(ctrl.notification)

        ctrl.runRebalancing("A B", "1000", "2026-01-01", "2026-02-01", 3, "equal", "")

        assert notes == [(False, "Strateji backtest servisi kullanılamıyor.")]


class TestStrategyTabQml:
    def _engine(self, ctrl=None):
        engine = QQmlApplicationEngine()
        engine.addImportPath(str(QML_DIR))
        self.warnings = []
        engine.warnings.connect(lambda items: self.warnings.extend(w.toString() for w in items))
        if ctrl is not None:
            engine.rootContext().setContextProperty("strategyBacktestController", ctrl)
        return engine

    def _load(self, engine):
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / "components" / "PlanningStrategyTab.qml")))
        if not component.isReady():
            pytest.fail("\n".join(err.toString() for err in component.errors()))
        return component, component.create()

    def test_compiles_without_controller(self, qapp):
        engine = self._engine()
        component, item = self._load(engine)

        assert item is not None
        assert self.warnings == []

    def test_run_calls_controller_with_form_values(self, qapp):
        service = FakeService(_rebalance_result())
        ctrl = _controller(service)
        engine = self._engine(ctrl)
        component, item = self._load(engine)

        QMetaObject.invokeMethod(item, "run")

        name, args = service.calls[0]
        assert name == "rebalancing"
        assert args[0].tickers == ["THYAO", "ASELS", "BIMAS"]
        assert args[1] == 3 and args[2] == "equal"  # varsayılan: 3 aylık, eşit ağırlık
        assert item.property("hasResult") is True
        assert self.warnings == []

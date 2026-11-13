"""Sürükle-bırak sıralama: izleme listeleri ve model portföyler (denetleyici + ReorderHandle)."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Q_ARG, Q_RETURN_ARG, QMetaObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from src.ui_qml.controllers.model_portfolio_controller import ModelPortfolioController
from src.ui_qml.controllers.watchlist_controller import WatchlistController

QML_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"


def _capture(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


def _watchlist_controller(qapp):
    service = MagicMock()
    service.get_all_watchlists.return_value = []
    container = SimpleNamespace(services=SimpleNamespace(watchlist_service=service))
    ctrl = WatchlistController(container)
    ctrl._watchlists = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}, {"id": 3, "name": "C"}]
    return ctrl, service


def test_move_watchlist_persists_new_order(qapp):
    ctrl, service = _watchlist_controller(qapp)
    changed = _capture(ctrl.watchlistsChanged)

    ctrl.moveWatchlist(0, 2)

    service.reorder_watchlists.assert_called_once_with([2, 3, 1])
    assert [w["id"] for w in ctrl.watchlists] == [2, 3, 1] and changed


def test_move_watchlist_ignores_invalid_or_noop_moves(qapp):
    ctrl, service = _watchlist_controller(qapp)

    ctrl.moveWatchlist(1, 1)
    ctrl.moveWatchlist(-1, 2)
    ctrl.moveWatchlist(0, 3)

    service.reorder_watchlists.assert_not_called()
    assert [w["id"] for w in ctrl.watchlists] == [1, 2, 3]


def test_move_watchlist_keeps_order_and_reports_when_save_fails(qapp):
    ctrl, service = _watchlist_controller(qapp)
    service.reorder_watchlists.side_effect = RuntimeError("db kilitli")
    results = _capture(ctrl.actionCompleted)

    ctrl.moveWatchlist(2, 0)

    assert [w["id"] for w in ctrl.watchlists] == [1, 2, 3]
    assert results[-1][0] is False and "db kilitli" in results[-1][1]


def _portfolio_controller(qapp):
    ctrl = ModelPortfolioController(container=MagicMock())
    ctrl._service = MagicMock()
    ctrl._portfolio_list = [{"portfolioId": 10}, {"portfolioId": 20}, {"portfolioId": 30}]
    return ctrl


def test_move_portfolio_persists_new_order(qapp):
    ctrl = _portfolio_controller(qapp)
    changed = _capture(ctrl.portfolioListChanged)

    ctrl.movePortfolio(2, 0)

    ctrl._service.reorder_portfolios.assert_called_once_with([30, 10, 20])
    assert [p["portfolioId"] for p in ctrl.portfolioList] == [30, 10, 20] and changed


def test_move_portfolio_failure_keeps_order(qapp):
    ctrl = _portfolio_controller(qapp)
    ctrl._service.reorder_portfolios.side_effect = RuntimeError("yazılamadı")
    results = _capture(ctrl.operationResult)

    ctrl.movePortfolio(0, 1)
    ctrl.movePortfolio(0, 0)  # etkisiz

    assert [p["portfolioId"] for p in ctrl.portfolioList] == [10, 20, 30]
    assert results[-1][0] is False


def test_reorder_handle_computes_target_index_and_clamps(qapp):
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    warnings = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / "components/ReorderHandle.qml")))
    if not component.isReady():
        pytest.fail("; ".join(e.toString() for e in component.errors()))
    handle = component.create()
    handle.setProperty("rowIndex", 1)
    handle.setProperty("rowCount", 4)
    handle.setProperty("step", 50.0)

    def call(delta):
        result = QMetaObject.invokeMethod(handle, "targetIndex", Q_RETURN_ARG("QVariant"), Q_ARG("QVariant", delta))
        return int(result)

    assert call(0) == 1
    assert call(110) == 3   # iki satır aşağı
    assert call(-60) == 0   # bir satır yukarı
    assert call(5000) == 3  # alt sınır
    assert call(-5000) == 0  # üst sınır
    assert warnings == [], "; ".join(warnings)

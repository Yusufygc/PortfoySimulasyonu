"""Listeye hisse eklerken kod doğrulaması: bilinen kodlar doğrudan, bilinmeyenler çevrimiçi doğrulamayla eklenir."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import QCoreApplication

from src.ui_qml.controllers.watchlist_controller import WatchlistController


class ImmediateExecutor:
    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)


def _controller(known: bool, online_valid: bool = False):
    watchlist_service = MagicMock()
    watchlist_service.get_all_watchlists.return_value = []
    lookup = MagicMock()
    lookup.is_known_ticker.return_value = known
    lookup.verify_ticker_online.return_value = online_valid
    container = SimpleNamespace(services=SimpleNamespace(watchlist_service=watchlist_service), stock_lookup_service=lookup)
    ctrl = WatchlistController(container=container)
    ctrl._executor = ImmediateExecutor()
    results = []
    ctrl.actionCompleted.connect(lambda ok, msg: results.append((ok, msg)))
    return ctrl, watchlist_service, lookup, results


def test_known_ticker_is_added_without_online_check(qapp):
    ctrl, service, lookup, results = _controller(known=True)

    ctrl.addStock(1, "thyao.is", "not")
    QCoreApplication.processEvents()

    service.add_stock_by_ticker.assert_called_once_with(1, "THYAO", "not")
    lookup.verify_ticker_online.assert_not_called()
    assert results and results[-1][0] is True


def test_unknown_ticker_is_added_after_successful_online_verification(qapp):
    ctrl, service, lookup, results = _controller(known=False, online_valid=True)

    ctrl.addStock(1, "ABCDE", "")
    QCoreApplication.processEvents()

    lookup.verify_ticker_online.assert_called_once_with("ABCDE")
    service.add_stock_by_ticker.assert_called_once_with(1, "ABCDE", "")
    assert results[-1][0] is True


def test_unknown_ticker_failing_verification_is_rejected_and_not_stored(qapp):
    ctrl, service, _lookup, results = _controller(known=False, online_valid=False)

    ctrl.addStock(1, "ZZZZZ", "")
    QCoreApplication.processEvents()

    service.add_stock_by_ticker.assert_not_called()
    assert results == [(False, "Geçersiz hisse kodu: ZZZZZ")]

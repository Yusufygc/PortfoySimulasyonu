"""PriceRefreshController: kaynak sinyallerinin tek yenilemeye birleşmesi, son güncelleme ve tek yenile ikonu."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtCore import QObject, QSettings, Signal

from src.ui_qml.controllers.price_refresh_controller import PriceRefreshController
from src.ui_qml.last_update_store import LastUpdateStore


class _Source(QObject):
    fired = Signal()


class _System(QObject):
    busyChanged = Signal()

    def __init__(self, session_open: bool):
        super().__init__()
        self.isRefreshing = False
        self._open = session_open
        self.started = 0

    def session_open(self) -> bool:
        return self._open

    def start_refresh(self) -> None:
        self.started += 1


class _MarketSync(QObject):
    isSyncingChanged = Signal()

    def __init__(self):
        super().__init__()
        self.isSyncing = False
        self.triggered = 0

    def triggerSyncNow(self) -> None:
        self.triggered += 1


class _EventBus(QObject):
    prices_updated = Signal(object)


@pytest.fixture
def store(tmp_path):
    return LastUpdateStore(QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))


def _controller(store, session_open=False, container=None):
    system, sync = _System(session_open), _MarketSync()
    ctrl = PriceRefreshController(system, sync, container=container, store=store)
    changed = []
    ctrl.pricesChanged.connect(lambda: changed.append(1))
    return ctrl, system, sync, changed


def test_burst_of_sources_coalesces_into_single_reload(qapp, store, wait_until):
    ctrl, _, _, changed = _controller(store)
    sources = [_Source() for _ in range(5)]
    for index, source in enumerate(sources):
        ctrl.watch(source.fired, records_update=index % 2 == 0)

    for source in sources:
        source.fired.emit()

    assert changed == []  # henüz birleştirme süresi dolmadı
    assert wait_until(lambda: len(changed) == 1)
    assert ctrl.lastUpdateText.startswith("Son güncelleme: ")


def test_portfolio_change_reloads_without_recording_update_time(qapp, store, wait_until):
    ctrl, _, _, changed = _controller(store)
    source = _Source()
    ctrl.watch(source.fired, records_update=False)

    source.fired.emit()

    assert wait_until(lambda: len(changed) == 1)
    assert ctrl.lastUpdateText == "" and store.prices_last_update() is None


def test_event_bus_prices_trigger_reload(qapp, store, wait_until):
    bus = _EventBus()
    ctrl, _, _, changed = _controller(store, container=SimpleNamespace(event_bus=bus))

    bus.prices_updated.emit({})  # boş: yenileme yok
    bus.prices_updated.emit({1: 10})

    assert wait_until(lambda: len(changed) == 1)
    assert store.prices_last_update() is not None


def test_refresh_icon_uses_live_refresh_in_session_and_close_sync_outside(qapp, store):
    in_session, system, sync, _ = _controller(store, session_open=True)
    in_session.refreshNow()
    assert (system.started, sync.triggered) == (1, 0)

    after_close, system, sync, _ = _controller(store, session_open=False)
    after_close.refreshNow()
    assert (system.started, sync.triggered) == (0, 1)


def test_refresh_icon_is_ignored_while_busy(qapp, store):
    ctrl, system, sync, _ = _controller(store, session_open=False)
    busy = []
    ctrl.busyChanged.connect(lambda: busy.append(1))
    sync.isSyncing = True
    sync.isSyncingChanged.emit()

    ctrl.refreshNow()

    assert ctrl.isRefreshing is True and busy and sync.triggered == 0

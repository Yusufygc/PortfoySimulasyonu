import sys
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget

from src.application.services.market.live_price_refresh_service import LivePriceRefreshResult
from src.ui.shared.live_price_refresh_controller import (
    LAST_LIVE_PRICE_REFRESH_KEY,
    LIVE_PRICE_REFRESH_ENABLED_KEY,
    LIVE_PRICE_REFRESH_INTERVAL_KEY,
    LivePriceRefreshController,
)


app = QApplication.instance()
if app is None:
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    app = QApplication(sys.argv)


class DummySettings:
    def __init__(self, values=None):
        self.values = dict(values or {})
        self.synced = False

    def value(self, key, default=None):
        return self.values.get(key, default)

    def setValue(self, key, value):
        self.values[key] = value

    def sync(self):
        self.synced = True


class DummyThreadPool:
    def __init__(self):
        self.started = []

    def start(self, worker):
        self.started.append(worker)


class DummySignal:
    def __init__(self):
        self.emitted = []

    def emit(self, payload):
        self.emitted.append(payload)


class DummyLivePriceRefreshService:
    def refresh_active_prices(self):
        return LivePriceRefreshResult(
            scanned_count=1,
            updated_count=1,
            prices={1: Decimal("10")},
        )


def make_controller(settings=None, is_open=True):
    parent = QWidget()
    threadpool = DummyThreadPool()
    container = SimpleNamespace(
        live_price_refresh_service=DummyLivePriceRefreshService(),
        event_bus=SimpleNamespace(prices_updated=DummySignal()),
        bist_market_session_service=SimpleNamespace(
            status_for=lambda day: SimpleNamespace(is_open=is_open)
        ),
    )
    controller = LivePriceRefreshController(
        parent=parent,
        container=container,
        settings=settings or DummySettings(),
        threadpool=threadpool,
    )
    return controller, parent, container, threadpool


def test_live_price_refresh_defaults_to_enabled_15_minutes_timer():
    controller, parent, _, _ = make_controller()

    controller.reload_settings()

    assert controller.enabled() is True
    assert controller.interval_minutes() == 15
    assert controller._timer.isActive()
    assert controller._timer.interval() == 15 * 60_000
    parent.deleteLater()


def test_live_price_refresh_does_not_start_worker_when_disabled():
    settings = DummySettings({LIVE_PRICE_REFRESH_ENABLED_KEY: False})
    controller, parent, _, threadpool = make_controller(settings=settings)

    controller.run_once()

    assert threadpool.started == []
    parent.deleteLater()


def test_live_price_refresh_does_not_start_worker_when_bist_closed():
    controller, parent, _, threadpool = make_controller(is_open=False)

    controller.run_once()

    assert threadpool.started == []
    parent.deleteLater()


def test_live_price_refresh_running_guard_prevents_overlapping_workers():
    controller, parent, _, threadpool = make_controller()

    controller.run_once()
    controller.run_once()

    assert len(threadpool.started) == 1
    parent.deleteLater()


def test_live_price_refresh_uses_configured_interval():
    settings = DummySettings({LIVE_PRICE_REFRESH_INTERVAL_KEY: 30})
    controller, parent, _, _ = make_controller(settings=settings)

    controller.reload_settings()

    assert controller.interval_minutes() == 30
    assert controller._timer.interval() == 30 * 60_000
    parent.deleteLater()


def test_live_price_refresh_success_publishes_event_and_records_timestamp():
    settings = DummySettings()
    controller, parent, container, _ = make_controller(settings=settings)
    finished_at = datetime(2026, 6, 3, 9, 45, tzinfo=timezone.utc)

    controller._on_success(
        LivePriceRefreshResult(
            scanned_count=2,
            updated_count=1,
            prices={7: Decimal("42.25")},
            errors=["BBB.IS: fiyat bulunamadi."],
            finished_at=finished_at,
        )
    )

    assert container.event_bus.prices_updated.emitted == [{7: Decimal("42.25")}]
    assert settings.values[LAST_LIVE_PRICE_REFRESH_KEY] == "2026-06-03T09:45:00+00:00"
    assert settings.synced is True
    parent.deleteLater()

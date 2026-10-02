"""SystemController: otomatik canlı fiyat yenileme ayarı ve sistem sıfırlama (QML Ayarlar > Sistem)."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QSettings, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from src.ui_qml.controllers.system_controller import (
    LAST_LIVE_PRICE_REFRESH_KEY,
    LIVE_PRICE_REFRESH_ENABLED_KEY,
    LIVE_PRICE_REFRESH_INTERVAL_KEY,
    SystemController,
)

QML_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"


class ImmediateExecutor:
    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)


def _capture(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


def _container(session_open=True):
    container = MagicMock()
    container.bist_market_session_service.status_for.return_value = SimpleNamespace(is_open=session_open)
    container.live_price_refresh_service.refresh_active_prices.return_value = SimpleNamespace(
        prices={1: Decimal("10")}, updated_count=1, finished_at=datetime(2026, 10, 3, 12, 30, tzinfo=timezone.utc)
    )
    return container


def _ctrl(qapp, tmp_path, container):
    settings = QSettings(str(tmp_path / "system.ini"), QSettings.Format.IniFormat)
    ctrl = SystemController(container=container, settings=settings, autostart=False)
    ctrl._executor = ImmediateExecutor()
    return ctrl, settings


def test_defaults_and_persisted_settings(qapp, tmp_path):
    ctrl, settings = _ctrl(qapp, tmp_path, _container())

    assert ctrl.liveRefreshEnabled is True and ctrl.liveRefreshInterval == 15
    assert [o["minutes"] for o in ctrl.intervalOptions] == [5, 15, 30, 60]
    assert ctrl._timer.isActive() and ctrl._timer.interval() == 15 * 60_000

    ctrl.setLiveRefreshInterval(5)
    ctrl.setLiveRefreshInterval(7)  # geçersiz aralık yok sayılır
    assert ctrl.liveRefreshInterval == 5 and ctrl._timer.interval() == 5 * 60_000
    assert int(settings.value(LIVE_PRICE_REFRESH_INTERVAL_KEY)) == 5

    ctrl.setLiveRefreshEnabled(False)
    assert ctrl.liveRefreshEnabled is False and not ctrl._timer.isActive()
    assert str(settings.value(LIVE_PRICE_REFRESH_ENABLED_KEY)).lower() in {"false", "0"}


def test_refresh_publishes_prices_remembers_time_and_signals(qapp, tmp_path):
    container = _container()
    ctrl, settings = _ctrl(qapp, tmp_path, container)
    refreshed = _capture(ctrl.pricesRefreshed)

    ctrl.refreshNow()

    container.live_price_refresh_service.refresh_active_prices.assert_called_once_with()
    container.event_bus.prices_updated.emit.assert_called_once_with({1: Decimal("10")})
    assert refreshed and ctrl.isRefreshing is False
    assert str(settings.value(LAST_LIVE_PRICE_REFRESH_KEY)).startswith("2026-10-03T12:30")
    assert ctrl.lastRefreshText == "03.10.2026 12:30"


def test_refresh_skipped_when_disabled_session_closed_or_no_service(qapp, tmp_path):
    closed = _container(session_open=False)
    ctrl, _ = _ctrl(qapp, tmp_path, closed)
    ctrl.refreshNow()
    closed.live_price_refresh_service.refresh_active_prices.assert_not_called()

    opened = _container()
    (tmp_path / "x").mkdir()
    ctrl2, _ = _ctrl(qapp, tmp_path / "x", opened)
    ctrl2.setLiveRefreshEnabled(False)
    opened.live_price_refresh_service.refresh_active_prices.reset_mock()
    ctrl2.refreshNow()
    opened.live_price_refresh_service.refresh_active_prices.assert_not_called()

    bare, _ = _ctrl(qapp, tmp_path, None)
    bare.refreshNow()  # servis yok: sessizce çıkar


def test_repeated_refresh_errors_notify_only_after_threshold(qapp, tmp_path):
    container = _container()
    container.live_price_refresh_service.refresh_active_prices.side_effect = RuntimeError("ağ yok")
    ctrl, _ = _ctrl(qapp, tmp_path, container)
    notes = _capture(ctrl.notification)

    ctrl.refreshNow()
    ctrl.refreshNow()
    assert notes == []
    ctrl.refreshNow()

    assert len(notes) == 1 and notes[0][0] is False and "ağ yok" in notes[0][1]


def test_reset_runs_service_and_requests_reload(qapp, tmp_path):
    container = _container()
    ctrl, _ = _ctrl(qapp, tmp_path, container)
    notes, resets = _capture(ctrl.notification), _capture(ctrl.systemReset)

    ctrl.resetAll()

    container.reset_service.reset_all.assert_called_once_with()
    assert resets and notes[-1][0] is True and ctrl.isResetting is False


def test_reset_failure_is_reported_without_reload(qapp, tmp_path):
    container = _container()
    container.reset_service.reset_all.side_effect = RuntimeError("kilitli")
    ctrl, _ = _ctrl(qapp, tmp_path, container)
    notes, resets = _capture(ctrl.notification), _capture(ctrl.systemReset)

    ctrl.resetAll()

    assert resets == [] and notes[-1][0] is False and "kilitli" in notes[-1][1]
    assert ctrl.isResetting is False


def test_system_tab_and_confirm_dialog_compile(qapp, tmp_path):
    ctrl, _ = _ctrl(qapp, tmp_path, _container())
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    warnings = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    engine.rootContext().setContextProperty("systemController", ctrl)

    for path in ("components/ConfirmDialog.qml", "components/SettingsSystemTab.qml"):
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / path)))
        if not component.isReady():
            pytest.fail(f"{path}: " + "\n".join(e.toString() for e in component.errors()))
        assert component.create() is not None, path

    assert warnings == [], "\n".join(warnings)

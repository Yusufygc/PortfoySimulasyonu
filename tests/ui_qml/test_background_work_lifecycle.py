"""Arka plan işi denetleyiciden uzun yaşamaz.

2026-11-08 CI çökmesi (`Windows fatal exception: access violation`, `test_market_sync_controller_trigger_sync`):
`create_controllers(autostart=False)` `SystemController` ve `MarketTickerController`'a bayrağı iletmiyordu; testler
gerçek yfinance çağrısı başlatıyor, sonuç silinmiş denetleyiciye sinyal olarak dönüyor ve başka bir testin olay
döngüsünde süreç çöküyordu. Gecikmeli işler `QTimer.singleShot(ms, self.metot)` ile kurulduğundan iptal edilemiyordu.
"""
from __future__ import annotations

import ast
import inspect
import time
from pathlib import Path

import shiboken6
from PySide6.QtCore import QCoreApplication, QObject

from src.ui_qml.controllers.registry import AUTOSTART, CONTROLLERS
from src.ui_qml.deferred import cancel_pending, pending_count, run_later

UI_DIR = Path(__file__).resolve().parents[2] / "src" / "ui_qml"


def _spin(ms: int) -> None:
    deadline = time.monotonic() + ms / 1000
    while time.monotonic() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.005)


def test_registry_forwards_autostart_to_every_controller_that_accepts_it():
    missing = [
        name for name, cls, options in CONTROLLERS
        if "autostart" in inspect.signature(cls.__init__).parameters and "autostart" not in options
    ]
    assert not missing, f"autostart bayrağı iletilmiyor (testte arka plan işi başlar): {missing}"
    assert all(options["autostart"] in (AUTOSTART, False) for _, _, options in CONTROLLERS if "autostart" in options)


def test_run_later_fires_once(qapp):
    owner, calls = QObject(), []
    run_later(owner, 10, lambda: calls.append(1))
    _spin(80)
    assert calls == [1] and pending_count() == 0


def test_run_later_does_not_fire_after_owner_is_deleted(qapp):
    owner, calls = QObject(), []
    run_later(owner, 30, lambda: calls.append(1))
    shiboken6.delete(owner)  # QML motoru kapanınca olduğu gibi C++ nesnesi silinir
    _spin(100)
    assert calls == []


def test_cancel_pending_stops_scheduled_work(qapp):
    owner, calls = QObject(), []
    run_later(owner, 30, lambda: calls.append(1))
    assert pending_count() == 1
    cancel_pending()
    _spin(100)
    assert calls == [] and pending_count() == 0


def test_controllers_do_not_use_uncancellable_single_shot():
    offenders = []
    for path in UI_DIR.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Attribute) and node.attr == "singleShot":
                offenders.append(f"{path.relative_to(UI_DIR).as_posix()}:{node.lineno}")
    assert not offenders, f"QTimer.singleShot iptal edilemez; src/ui_qml/deferred.run_later kullanın: {offenders}"

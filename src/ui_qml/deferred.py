"""Sahibine bağlı, iptal edilebilir gecikmeli iş (`QTimer.singleShot` yerine).

`QTimer.singleShot(ms, self.metot)` iptal edilemez ve sahibinden bağımsız ateşlenir: denetleyici silinse ya da test
bitse de saniyeler sonra arka plan işi başlatır, sonuç silinmiş nesneye döner (2026-11-08 CI çökmesi). Burada
zamanlayıcı sahibinin Qt çocuğudur (sahip silinince ateşlenmez) ve testler bekleyenleri `cancel_pending` ile durdurur.
"""
from __future__ import annotations

import weakref
from typing import Callable

import shiboken6
from PySide6.QtCore import QObject, QTimer

_PENDING: "weakref.WeakSet[QTimer]" = weakref.WeakSet()


def run_later(owner: QObject, delay_ms: int, callback: Callable[[], object]) -> QTimer:
    """`delay_ms` sonra `callback`'i bir kez çağırır; `owner` silinmişse veya iş iptal edildiyse çağırmaz."""
    timer = QTimer(owner)
    timer.setSingleShot(True)

    def fire() -> None:
        _PENDING.discard(timer)
        if shiboken6.isValid(owner):
            callback()

    timer.timeout.connect(fire)
    _PENDING.add(timer)
    timer.start(delay_ms)
    return timer


def pending_count() -> int:
    return sum(1 for timer in list(_PENDING) if shiboken6.isValid(timer) and timer.isActive())


def cancel_pending() -> None:
    """Bekleyen tüm gecikmeli işleri durdurur (test bitişi)."""
    for timer in list(_PENDING):
        if shiboken6.isValid(timer):
            timer.stop()
    _PENDING.clear()

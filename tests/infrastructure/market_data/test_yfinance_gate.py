"""yfinance kapısı: normal serileştirme, takılan tutucuya karşı fail-open ve doğru serbest bırakma."""
from __future__ import annotations

import threading

from src.infrastructure.market_data.yfinance_lock import YFinanceGate


def test_gate_serializes_concurrent_entries():
    gate = YFinanceGate(timeout=5)
    inside = []
    overlap = []
    release_first = threading.Event()
    first_in = threading.Event()

    def first():
        with gate:
            inside.append("first")
            first_in.set()
            release_first.wait(timeout=5)
            inside.remove("first")

    def second():
        first_in.wait(timeout=5)
        with gate:
            overlap.append(list(inside))

    t1, t2 = threading.Thread(target=first), threading.Thread(target=second)
    t1.start(); t2.start()
    first_in.wait(timeout=5)
    release_first.set()
    t1.join(timeout=5); t2.join(timeout=5)

    assert overlap == [[]]  # ikinci giriş, birincinin bitmesinden sonra gerçekleşti


def test_gate_fails_open_when_holder_is_stuck_and_does_not_release_foreign_lock():
    gate = YFinanceGate(timeout=0.05)
    holder_ready, holder_stop = threading.Event(), threading.Event()

    def holder():
        with gate:
            holder_ready.set()
            holder_stop.wait(timeout=5)

    thread = threading.Thread(target=holder)
    thread.start()
    holder_ready.wait(timeout=5)

    entered = False
    with gate:  # zaman aşımı: kilitsiz devam eder
        entered = True
    still_held = not gate._lock.acquire(blocking=False)  # tutucunun kilidi bozulmamalı

    holder_stop.set()
    thread.join(timeout=5)
    assert entered and still_held
    assert gate._lock.acquire(blocking=False), "tutucu çıkınca kilit serbest kalmalı"
    gate._lock.release()


def test_gate_releases_after_exception_inside_block():
    gate = YFinanceGate(timeout=1)

    try:
        with gate:
            raise ValueError("boom")
    except ValueError:
        pass

    assert gate._lock.acquire(blocking=False)
    gate._lock.release()


def test_gate_nested_use_in_one_thread_does_not_deadlock_after_timeout():
    gate = YFinanceGate(timeout=0.05)

    with gate:
        with gate:  # aynı iş parçacığında iç içe giriş: zaman aşımından sonra kilitsiz geçer
            pass
        assert not gate._lock.acquire(blocking=False)  # dış giriş hâlâ kilidi tutuyor

    assert gate._lock.acquire(blocking=False)
    gate._lock.release()

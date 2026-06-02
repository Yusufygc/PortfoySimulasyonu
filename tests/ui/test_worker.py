from src.ui.worker import Worker


def test_worker_emits_result_before_finished():
    events = []
    worker = Worker(lambda: "ok")

    worker.signals.result.connect(lambda result: events.append(("result", result)))
    worker.signals.finished.connect(lambda: events.append(("finished", None)))

    worker.run()

    assert events == [("result", "ok"), ("finished", None)]


def test_worker_emits_error_before_finished():
    events = []

    def fail():
        raise ValueError("boom")

    worker = Worker(fail)
    worker.signals.error.connect(lambda err: events.append(("error", err[0], str(err[1]))))
    worker.signals.finished.connect(lambda: events.append(("finished", None, None)))

    worker.run()

    assert events[0] == ("error", ValueError, "boom")
    assert events[1] == ("finished", None, None)

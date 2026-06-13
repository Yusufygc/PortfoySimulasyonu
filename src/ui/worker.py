import logging
import sys
import traceback
from uuid import uuid4

from src.qt_compat.qtcore import QObject, QRunnable, Signal, Slot


logger = logging.getLogger(__name__)


class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    cleanup = Signal()

    def __init__(self):
        super().__init__()
        self._cleanup_callback = None
        self.cleanup.connect(self._cleanup_worker)

    def set_cleanup_callback(self, callback) -> None:
        self._cleanup_callback = callback

    @Slot()
    def _cleanup_worker(self) -> None:
        if self._cleanup_callback is not None:
            self._cleanup_callback()


class Worker(QRunnable):
    _active_workers = set()

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.job_id = uuid4().hex[:12]
        self._active_workers.add(self)
        self.signals.set_cleanup_callback(self._release)

    def _release(self) -> None:
        self._active_workers.discard(self)

    @Slot()
    def run(self):
        operation = getattr(self.fn, "__name__", self.fn.__class__.__name__)
        logger.info("Worker job started: job_id=%s operation=%s", self.job_id, operation)
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception:
            logger.exception("Worker job failed: job_id=%s operation=%s", self.job_id, operation)
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            logger.info("Worker job finished: job_id=%s operation=%s", self.job_id, operation)
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()
            self.signals.cleanup.emit()

import logging
import sys
import traceback
from uuid import uuid4

from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot


logger = logging.getLogger(__name__)


class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)


class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.job_id = uuid4().hex[:12]

    @pyqtSlot()
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

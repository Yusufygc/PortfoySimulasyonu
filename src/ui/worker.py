# src/ui/worker.py

import sys
import traceback
import logging
from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

logger = logging.getLogger(__name__)

class WorkerSignals(QObject):
    """
    Worker iş parçacığı sinyallerini tanımlar.
    
    Sinyaller:
    - finished: İşlem bittiğinde tetiklenir (başarılı veya başarısız fark etmeksizin).
    - error: İşlem sırasında istisna (exception) oluştuğunda tetiklenir (tuple: exctype, value, traceback_str).
    - result: İşlem başarıyla döndüğünde sonucu taşır.
    """
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)


class Worker(QRunnable):
    """
    QThreadPool ile çalıştırılabilir genel amaçlı Worker sınıfı.
    Ağ aramaları (örn. yfinance) ve uzun DB sorguları için kullanılır.
    """
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            logger.exception("Worker thread içinde hata oluştu:")
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()

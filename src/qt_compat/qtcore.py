"""QtCore compatibility exports for PySide6."""

from datetime import date, time

from PySide6.QtCore import *  # noqa: F403
from PySide6.QtCore import QDate, QTime, Signal, Slot


def _qdate_to_pydate(self: QDate) -> date:
    return date(self.year(), self.month(), self.day())


def _qtime_to_pytime(self: QTime) -> time:
    return time(self.hour(), self.minute(), self.second(), self.msec() * 1000)


if not hasattr(QDate, "toPyDate"):
    QDate.toPyDate = _qdate_to_pydate

if not hasattr(QTime, "toPyTime"):
    QTime.toPyTime = _qtime_to_pytime


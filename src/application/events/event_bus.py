from __future__ import annotations

from PyQt5.QtCore import QObject, pyqtSignal


class GlobalEventBus(QObject):
    """Application-wide Qt signal bus used by UI and application services."""

    prices_updated = pyqtSignal(object)

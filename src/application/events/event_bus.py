from __future__ import annotations

from src.qt_compat.qtcore import QObject, Signal


class GlobalEventBus(QObject):
    """Application-wide Qt signal bus used by UI and application services."""

    prices_updated = Signal(object)

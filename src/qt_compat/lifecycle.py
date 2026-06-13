"""QObject lifecycle helpers for PySide6."""

from __future__ import annotations

from shiboken6 import isValid


def is_qobject_deleted(obj) -> bool:
    """Return True when a Qt object has already been deleted."""
    if obj is None:
        return True
    try:
        return not isValid(obj)
    except RuntimeError:
        return True

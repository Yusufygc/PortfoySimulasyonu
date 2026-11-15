"""Runtime display scaling helpers for Qt startup."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, MutableMapping


_DISABLE_ENV = "PORTFOYSIM_DISABLE_QT_SCALE_NORMALIZATION"
_QT_SCALE_ENV = "QT_SCALE_FACTOR"
_QT_ROUNDING_ENV = "QT_SCALE_FACTOR_ROUNDING_POLICY"


def _windows_scale_percent() -> int | None:
    if sys.platform != "win32":
        return None
    try:
        import ctypes

        return int(ctypes.windll.shcore.GetScaleFactorForDevice(0))
    except Exception:
        return None


def qt_scale_factor_for_percent(scale_percent: int | None) -> str | None:
    """Deprecated inverse scale helper kept for compatibility; returns None.

    QML uses logical pixels with native Qt6 Per-Monitor DPI scaling, so
    counter-scaling Windows display percentages (e.g. 200% -> 0.5) shrinks the
    entire interface on high-DPI laptop screens.
    """
    _ = scale_percent
    return None


def configure_qt_scale_normalization(
    env: MutableMapping[str, str] | None = None,
    scale_percent_provider: Callable[[], int | None] | None = None,
) -> str | None:
    """Configure Qt6 high-DPI rounding policy on Windows before QApplication exists.

    QML layouts follow Qt6's native Per-Monitor DPI scaling, so we no longer
    override ``QT_SCALE_FACTOR`` with an inverse factor. Instead, we ensure
    fractional Windows scales (125%, 150%) use ``PassThrough`` rounding unless
    explicitly overridden by the user.
    """
    _ = scale_percent_provider
    env = env if env is not None else os.environ
    if env.get(_DISABLE_ENV) == "1" or env.get(_QT_SCALE_ENV):
        return None

    env.setdefault(_QT_ROUNDING_ENV, "PassThrough")
    return env[_QT_ROUNDING_ENV]

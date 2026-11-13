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
    """Return the inverse Qt scale factor needed to keep 100% UI density."""
    if scale_percent is None or scale_percent <= 100:
        return None
    factor = max(0.5, min(1.0, 100.0 / float(scale_percent)))
    return f"{factor:.3f}".rstrip("0").rstrip(".")


def configure_qt_scale_normalization(
    env: MutableMapping[str, str] | None = None,
    scale_percent_provider: Callable[[], int | None] | None = None,
) -> str | None:
    """Normalize Qt6 high-DPI scaling on Windows before QApplication exists.

    PySide6/Qt6 applies Windows display scaling by default. The existing UI was
    tuned around physical pixels, so a 125% desktop scale makes fixed widgets
    and QSS px tokens visibly larger. We counter-scale only when the user has
    not supplied an explicit Qt scale factor.
    """
    env = env if env is not None else os.environ
    if env.get(_DISABLE_ENV) == "1" or env.get(_QT_SCALE_ENV):
        return None

    provider = scale_percent_provider or _windows_scale_percent
    factor = qt_scale_factor_for_percent(provider())
    if factor is None:
        return None

    env[_QT_SCALE_ENV] = factor
    env.setdefault(_QT_ROUNDING_ENV, "PassThrough")
    return factor

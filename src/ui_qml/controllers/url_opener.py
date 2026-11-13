"""Dış kaynaktan gelen bağlantıları varsayılan tarayıcıda güvenle açar (yalnızca http/https)."""
from __future__ import annotations

import logging

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

logger = logging.getLogger(__name__)

ALLOWED_SCHEMES = ("http", "https")


def open_external_url(url: str) -> bool:
    """`file:`, `javascript:` ve diğer şemaları reddeder (yerel dosya/uygulama açılmasını önler)."""
    target = QUrl((url or "").strip())
    if not target.isValid() or target.scheme().lower() not in ALLOWED_SCHEMES or not target.host():
        logger.warning("Dış bağlantı reddedildi (şema/host): %s", url)
        return False
    return bool(QDesktopServices.openUrl(target))

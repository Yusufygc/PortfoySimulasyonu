"""Dashboard HTML'i görüntüleyen WebView paneli."""
from __future__ import annotations

import os
import tempfile
import logging

from src.qt_compat.qtcore import QUrl
from src.qt_compat.qtwidgets import QVBoxLayout, QWidget
from src.ui.widgets.shared.controls.silent_web_view import SilentWebEngineView
from src.ui.shared.locale_tr import L10N

logger = logging.getLogger(__name__)


class FinancialsChartPanel(QWidget):
    """SilentWebEngineView içinde finansal dashboard HTML gösterir."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._temp_file: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._view = SilentWebEngineView(self)
        layout.addWidget(self._view)

        self._show_placeholder()

    # ------------------------------------------------------------------

    def load_html(self, html: str) -> None:
        """Dashboard HTML'ini temp dosyaya yaz, WebView'e yükle."""
        self._cleanup_temp()
        try:
            fd, path = tempfile.mkstemp(suffix=".html", prefix="portfoy_fin_")
            os.close(fd)
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            self._temp_file = path
            self._view.setUrl(QUrl.fromLocalFile(path))
        except Exception:
            logger.exception("Finansal dashboard HTML yüklenemedi")
            self._show_error(L10N.GRAFIK_YUKLENEMEDI)

    def show_error(self, message: str) -> None:
        self._cleanup_temp()
        self._show_error(message)

    def clear(self) -> None:
        self._cleanup_temp()
        self._show_placeholder()

    def cleanup(self) -> None:
        self._cleanup_temp()

    # ------------------------------------------------------------------

    def _show_placeholder(self) -> None:
        html = (
            "<html><body style='background:#0f172a;color:#64748b;"
            "font-family:Segoe UI,sans-serif;text-align:center;padding-top:120px;'>"
            f"<p>{L10N.FINANSALLAR_GIRIS_ACIKLAMA}</p></body></html>"
        )
        self._view.setHtml(html)

    def _show_error(self, message: str) -> None:
        html = (
            "<html><body style='background:#0f172a;color:#ef4444;"
            "font-family:Segoe UI,sans-serif;text-align:center;padding-top:120px;'>"
            f"<p>⚠️ {message}</p></body></html>"
        )
        self._view.setHtml(html)

    def _cleanup_temp(self) -> None:
        if self._temp_file:
            try:
                if os.path.exists(self._temp_file):
                    os.remove(self._temp_file)
            except OSError:
                pass
            self._temp_file = None

"""
Stock 360 HTML — QML WebEngine için geçici HTML dosyalarını oluşturan ve yöneten servis.
"""
from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QUrl

from src.ui.pages.financials.utils.dashboard_html import build_dashboard as build_financials_dashboard_raw
from src.ui.pages.shareholders.utils.dashboard_html import build_dashboard as build_shareholder_dashboard_raw

logger = logging.getLogger(__name__)


def generate_financials_html(metrics: Dict[str, Any], n_periods: int) -> str:
    """Finansal bilanço ve rasyolar için etkileşimli HTML dashboard içeriğini üretir."""
    return build_financials_dashboard_raw(metrics, n_periods=n_periods)


def generate_shareholders_html(ticker: str, snapshots: List[Any]) -> str:
    """KAP ortaklık yapısı ve geçmişi için etkileşimli HTML dashboard içeriğini üretir."""
    return build_shareholder_dashboard_raw(ticker, snapshots)


def write_temp_html(prefix: str, ticker: str, content: str) -> Tuple[str, Optional[str]]:
    """
    HTML içeriğini geçici dosyaya kaydeder.
    Dönüş: (file_url_string, file_path_str)
    """
    try:
        temp_dir = Path(tempfile.gettempdir())
        filename = f"portfoy_{prefix}_{ticker}.html"
        file_path = temp_dir / filename
        file_path.write_text(content, encoding="utf-8")
        file_url = QUrl.fromLocalFile(str(file_path)).toString()
        return file_url, str(file_path)
    except Exception as exc:
        logger.exception("HTML geçici dosyaya yazılamadı [%s_%s]: %s", prefix, ticker, exc)
        return "", None


def cleanup_temp_files(file_paths: List[str]) -> None:
    """Geçici HTML dosyalarını diskten temizler."""
    for f in file_paths:
        try:
            if os.path.exists(f):
                os.remove(f)
        except OSError as exc:
            logger.debug("Geçici dosya silinemedi (%s): %s", f, exc)

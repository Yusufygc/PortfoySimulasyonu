# src/ui/theme_manager.py
import os
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFontDatabase, QFont

logger = logging.getLogger(__name__)

class ThemeManager:
    """
    Kullanıcı arayüzü temalarını (QSS) ve fontlarını yöneten merkezi sınıf.
    """

    @classmethod
    def apply_theme(cls, app: QApplication, theme_name: str = "dark_theme"):
        """Belirtilen temayı (QSS) uygulamaya uygular."""
        # 1. Font Yükleme (Opsiyonel: Google Inter fontu projenin assets klasöründe varsa yüklenebilir)
        # Şimdilik sistem default Segoe UI veya Arial kullanacağız.
        font = QFont("Segoe UI", 10)
        app.setFont(font)

        # 2. QSS'i Okuma ve Uygulama
        base_dir = os.path.dirname(os.path.abspath(__file__))
        qss_path = os.path.join(base_dir, "styles", f"{theme_name}.qss")
        
        try:
            if os.path.exists(qss_path):
                with open(qss_path, "r", encoding="utf-8") as f:
                    qss_content = f.read()
                    app.setStyleSheet(qss_content)
                    logger.info(f"Theme '{theme_name}' applied successfully.")
            else:
                logger.warning(f"Theme file not found: {qss_path}")
        except Exception as e:
            logger.error(f"Error applying theme {theme_name}: {e}")

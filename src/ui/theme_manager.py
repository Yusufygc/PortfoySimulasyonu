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

        # 2. QSS'i Okuma ve Uygulama (Modüler Yapı)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        styles_dir = os.path.join(base_dir, "styles")
        
        # Yüklenecek QSS dosyalarının sırası (Önce base/tema, sonra componentler)
        qss_files = [
            f"{theme_name}.qss",  # Ana tema ve değişkenler
            "typography.qss",     # Font ve yazı stilleri
            "components.qss",     # Butonlar, inputlar vb.
            "layout.qss"          # Frame, kart ve layout stilleri
        ]
        
        combined_qss = ""
        for file_name in qss_files:
            qss_path = os.path.join(styles_dir, file_name)
            if os.path.exists(qss_path):
                try:
                    with open(qss_path, "r", encoding="utf-8") as f:
                        combined_qss += f.read() + "\n"
                except Exception as e:
                    logger.error(f"Error reading {file_name}: {e}")
            else:
                # Tema ana dosyası haricindekiler opsiyonel olabilir, ama varsa loglayalım.
                if file_name == f"{theme_name}.qss":
                    logger.warning(f"Main theme file not found: {qss_path}")
                else:
                    logger.debug(f"Optional style file not found: {qss_path}")

        try:
            if combined_qss:
                app.setStyleSheet(combined_qss)
                logger.info(f"Theme '{theme_name}' and modules applied successfully.")
        except Exception as e:
            logger.error(f"Error applying combined stylesheet: {e}")

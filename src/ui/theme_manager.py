# src/ui/theme_manager.py
import os
import logging
from typing import Optional
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont, QFontDatabase

logger = logging.getLogger(__name__)


class ThemeManager:
    """
    Kullanıcı arayüzü temalarını (QSS) ve fontlarını yöneten merkezi sınıf.

    Design Token Sistemi:
    ---------------------
    QSS dosyaları içinde '@TOKEN_ADI' formatında değişken referansları
    kullanılabilir. Bu sınıf, tüm QSS içeriğini birleştirdikten sonra
    söz konusu referansları tokens.py'daki gerçek değerlerle değiştirir.

    Örnek QSS kullanımı:
        QPushButton { background-color: @COLOR_PRIMARY; font-size: @FONT_MD; }
    """

    @classmethod
    def apply_theme(
        cls,
        app: QApplication,
        theme_name: str = "dark_theme",
        token_overrides: Optional[dict] = None,
    ):
        """
        Belirtilen temayı (QSS) token değiştirmesiyle birlikte uygular.

        Args:
            app: QApplication nesnesi.
            theme_name: Kullanılacak ana QSS dosyasının adı (uzantısız).
            token_overrides: Varsayılan tokenların üzerine yazılacak ekstra
                             değerler (örn. Light Mode için).
        """
        # 1. Inter fontunu yükle (yoksa Segoe UI'ya düş)
        font_name = cls._load_inter_font()
        font = QFont(font_name, 10)
        font.setHintingPreference(QFont.PreferFullHinting)
        app.setFont(font)

        # 2. Design Tokenları yükle
        from src.ui.styles.tokens import DEFAULT_THEME
        tokens: dict[str, str] = {**DEFAULT_THEME}
        if token_overrides:
            tokens.update(token_overrides)

        # 3. QSS dosyalarını sırayla oku ve birleştir
        base_dir = os.path.dirname(os.path.abspath(__file__))
        styles_dir = os.path.join(base_dir, "styles")

        qss_files = [
            f"{theme_name}.qss",  # Ana tema / global base stiller
            "typography.qss",     # Yazı tipleri ve metin stilleri
            "components.qss",     # Butonlar, inputlar, form elemanları
            "layout.qss",         # Frame, kart ve layout stilleri
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
                if file_name == f"{theme_name}.qss":
                    logger.warning(f"Main theme file not found: {qss_path}")
                else:
                    logger.debug(f"Optional style file not found: {qss_path}")

        # 4. Token referanslarını (@TOKEN_ADI) gerçek değerlerle değiştir
        resolved_qss = cls._resolve_tokens(combined_qss, tokens)

        # 5. Uygula
        try:
            if resolved_qss:
                app.setStyleSheet(resolved_qss)
                logger.info(
                    f"Theme '{theme_name}' applied with {len(tokens)} design tokens."
                )
        except Exception as e:
            logger.error(f"Error applying combined stylesheet: {e}")

    @staticmethod
    def _resolve_tokens(qss: str, tokens: dict[str, str]) -> str:
        """
        QSS içindeki '@TOKEN_ADI' referanslarını token değerleriyle değiştirir.
        CSS yorum satırları (/* ... */) içindeki referanslar atlanır.
        Bilinmeyen referanslar loglanır ve olduğu gibi bırakılır.
        """
        import re

        # Yorum bloklarını önce korumak için placeholder sistemi
        comments: list[str] = []

        def save_comment(m: re.Match) -> str:
            comments.append(m.group(0))
            return f"__COMMENT_{len(comments) - 1}__"

        # Yorumları geçici olarak sakla
        qss_no_comments = re.sub(r"/\*.*?\*/", save_comment, qss, flags=re.DOTALL)

        def replace_token(match: re.Match) -> str:
            token_name = match.group(1)
            value = tokens.get(token_name)
            if value is None:
                logger.warning(f"[ThemeManager] Bilinmeyen token: @{token_name}")
                return match.group(0)  # Orijinalini koru
            return value

        resolved = re.sub(r"@([A-Z0-9_]+)", replace_token, qss_no_comments)

        # Yorumları geri yükle
        for i, comment in enumerate(comments):
            resolved = resolved.replace(f"__COMMENT_{i}__", comment)

        return resolved

    @classmethod
    def _load_inter_font(cls) -> str:
        """
        Inter font dosyalarını QFontDatabase'e yükler.
        Başarılı olursa 'Inter', aksi halde 'Segoe UI' döner.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        fonts_dir = os.path.join(base_dir, "fonts")

        font_files = [
            "Inter-Regular.ttf",
            "Inter-Medium.ttf",
            "Inter-SemiBold.ttf",
            "Inter-Bold.ttf",
        ]

        loaded = 0
        for filename in font_files:
            path = os.path.join(fonts_dir, filename)
            if os.path.exists(path):
                font_id = QFontDatabase.addApplicationFont(path)
                if font_id >= 0:
                    loaded += 1
                else:
                    logger.warning(f"[ThemeManager] Font yüklenemedi: {filename}")
            else:
                logger.debug(f"[ThemeManager] Font dosyası bulunamadı: {path}")

        if loaded > 0:
            logger.info(f"[ThemeManager] Inter font yüklendi ({loaded}/{len(font_files)} dosya).")
            return "Inter"

        logger.warning("[ThemeManager] Inter font bulunamadı, Segoe UI kullanılıyor.")
        return "Segoe UI"

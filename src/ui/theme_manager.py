# src/ui/theme_manager.py
import os
import logging
from typing import Optional
from src.qt_compat.qtcore import QSettings, Qt
from src.qt_compat.qtwidgets import QApplication
from src.qt_compat.qtgui import QFont, QFontDatabase

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------
#  Desteklenen temalar — yeni tema eklemek için buraya kayıt yap.
# ----------------------------------------------------------------
THEME_REGISTRY: dict[str, dict] = {
    "dark": {
        "display_name": "Koyu Tema",
        "description": "Göz yorgunluğunu azaltan, düşük ışıklı ortamlar için optimize edilmiş koyu renk paleti.",
        "qss_name": "dark_theme",
    },
    "light": {
        "display_name": "Açık Tema",
        "description": "Gün ışığında rahat okuma için yüksek kontrastlı, ferah açık renk paleti.",
        "qss_name": "light_theme",
    },
}

_SETTINGS_KEY = "ui/theme_id"
_QSETTINGS_APP = "PortfoySimulasyonu"



# Eski tema isimleri → yeni tema ID eşlemesi (geriye dönük uyum)
_LEGACY_NAME_MAP: dict[str, str] = {
    "dark_theme": "dark",
    "light_theme": "light",
}


class ThemeManager:
    """
    Merkezi tema yönetim sınıfı.

    KULLANIM:
        # İlk başlatma (app.py'de)
        ThemeManager.apply_theme(app)           # kayıtlı temayı yükle

        # Çalışma zamanında tema değiştir
        ThemeManager.switch_theme("light")

        # Mevcut tema ID'si
        ThemeManager.current_theme_id()         # → "dark" | "light"

    YENİ TEMA EKLEMEK:
        1. tokens.py'da yeni tema tokenlarını tanımla.
        2. themes/ klasörüne <tema_adı>.qss ekle.
        3. THEME_REGISTRY'e yeni girişi kaydet.
    """

    _app: Optional[QApplication] = None
    _current_theme_id: str = "dark"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def apply_theme(
        cls,
        app: QApplication,
        theme_id: str = "dark",
        token_overrides: Optional[dict] = None,
    ) -> None:
        """
        Temayı ilk kez yükler ve QApplication'a uygular.
        QSettings'te kayıtlı tercih varsa o kullanılır.
        """
        # QSettings'te kayıtlı tema varsa onu kullan
        saved = QSettings(_QSETTINGS_APP, _QSETTINGS_APP).value(_SETTINGS_KEY, "", type=str)
        if saved and saved in THEME_REGISTRY:
            theme_id = saved
        else:
            # Geriye dönük uyum: "dark_theme" → "dark"
            theme_id = _LEGACY_NAME_MAP.get(theme_id, theme_id)
            if theme_id not in THEME_REGISTRY:
                theme_id = "dark"

        cls._app = app
        cls._current_theme_id = theme_id
        cls._do_apply(theme_id, token_overrides)

    @classmethod
    def switch_theme(cls, theme_id: str) -> None:
        """Çalışma zamanında temayı değiştirir ve tercihi kaydeder."""
        if theme_id not in THEME_REGISTRY:
            logger.warning(f"[ThemeManager] Bilinmeyen tema: {theme_id}")
            return
        if cls._app is None:
            logger.warning("[ThemeManager] switch_theme çağrıldı ama _app henüz set edilmemiş.")
            return

        cls._current_theme_id = theme_id
        QSettings(_QSETTINGS_APP, _QSETTINGS_APP).setValue(_SETTINGS_KEY, theme_id)

        # İkon önbelleğini temizle; yeni ikonlar güncel tokenları kullanır.
        from src.ui.core.icon_manager import IconManager
        IconManager._icon_cache.clear()

        cls._do_apply(theme_id)

    @classmethod
    def current_theme_id(cls) -> str:
        return cls._current_theme_id

    @classmethod
    def available_themes(cls) -> dict[str, dict]:
        """Kayıtlı tüm temaları döner: {theme_id: {display_name, description, qss_name}}"""
        return THEME_REGISTRY

    @classmethod
    def build_theme_stylesheet(
        cls,
        theme_id: str,
        token_overrides: Optional[dict] = None,
    ) -> tuple[dict[str, str], str]:
        """Tema token haritasını ve çözülmüş QSS'i test edilebilir şekilde üretir."""
        from src.ui.styles.tokens import DARK_THEME, LIGHT_THEME

        normalized_theme_id = _LEGACY_NAME_MAP.get(theme_id, theme_id)
        if normalized_theme_id not in THEME_REGISTRY:
            normalized_theme_id = "dark"

        token_map: dict[str, dict] = {
            "dark": DARK_THEME,
            "light": LIGHT_THEME,
        }
        tokens: dict[str, str] = {**token_map.get(normalized_theme_id, DARK_THEME)}
        if token_overrides:
            tokens.update(token_overrides)

        qss_name = THEME_REGISTRY[normalized_theme_id]["qss_name"]
        return tokens, cls._build_qss(qss_name, tokens)

    @classmethod
    def validate_theme_tokens(cls, theme_id: str, token_overrides: Optional[dict] = None) -> list[str]:
        """Çözülmemiş tokenları döner; boş liste tema QSS'inin temiz olduğunu gösterir."""
        import re

        _, qss = cls.build_theme_stylesheet(theme_id, token_overrides)
        qss_without_comments = re.sub(r"/\*.*?\*/", "", qss, flags=re.DOTALL)
        return sorted(set(re.findall(r"@([A-Z0-9_]+)", qss_without_comments)))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @classmethod
    def _do_apply(cls, theme_id: str, token_overrides: Optional[dict] = None) -> None:
        import src.ui.styles.tokens as _tokens_mod

        tokens, resolved_qss = cls.build_theme_stylesheet(theme_id, token_overrides)

        # DEFAULT_THEME'i güncelle; IconManager token çözümlemesinde bunu kullanır.
        _tokens_mod.DEFAULT_THEME = tokens

        # Fontu yükle
        font_name = cls._load_inter_font()
        font = QFont(font_name, 10)
        font.setHintingPreference(QFont.PreferFullHinting)
        if cls._app and not cls._app.topLevelWidgets():
            cls._app.setFont(font)
        elif cls._app:
            logger.debug("[ThemeManager] Font apply skipped because widgets are already alive.")

        # QSS oluştur ve uygula
        if resolved_qss and cls._app:
            try:
                cls._app.setStyleSheet(resolved_qss)
                logger.info(
                    f"[ThemeManager] Tema uygulandı: '{theme_id}' "
                    f"({len(tokens)} token, dinamik QSS yüklendi)"
                )
            except Exception as e:
                logger.error(f"[ThemeManager] Stil uygulama hatası: {e}")

    @classmethod
    def _get_style_manifest(cls, qss_name: str) -> list[str]:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        styles_dir = os.path.join(base_dir, "styles")
        
        manifest = [f"themes/{qss_name}.qss"]
        import glob
        
        def add_from_dir(directory: str):
            pattern = os.path.join(styles_dir, directory, "**", "*.qss")
            files = glob.glob(pattern, recursive=True)
            for f in sorted(files):
                rel_path = os.path.relpath(f, styles_dir).replace("\\", "/")
                manifest.append(rel_path)
                
        add_from_dir("primitives")
        add_from_dir("shared")
        add_from_dir("features")
        
        return manifest

    @classmethod
    def _build_qss(cls, qss_name: str, tokens: dict[str, str]) -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        styles_dir = os.path.join(base_dir, "styles")

        combined_qss = ""
        manifest = cls._get_style_manifest(qss_name)
        for file_name in manifest:
            qss_path = os.path.join(styles_dir, file_name)
            if os.path.exists(qss_path):
                try:
                    with open(qss_path, "r", encoding="utf-8-sig") as f:
                        combined_qss += f.read().lstrip("﻿") + "\n"
                    logger.debug(f"[ThemeManager] Yüklendi: {file_name}")
                except Exception as e:
                    logger.error(f"[ThemeManager] Okuma hatası ({file_name}): {e}")
            else:
                if file_name == f"themes/{qss_name}.qss":
                    logger.warning(f"[ThemeManager] Ana tema dosyası bulunamadı: {qss_path}")
                else:
                    logger.debug(f"[ThemeManager] Opsiyonel stil bulunamadı: {qss_path}")

        return cls._resolve_tokens(combined_qss, tokens)

    @staticmethod
    def _resolve_tokens(qss: str, tokens: dict[str, str]) -> str:
        import re

        comments: list[str] = []

        def save_comment(m: re.Match) -> str:
            comments.append(m.group(0))
            return f"__COMMENT_{len(comments) - 1}__"

        qss_no_comments = re.sub(r"/\*.*?\*/", save_comment, qss, flags=re.DOTALL)

        def replace_token(match: re.Match) -> str:
            token_name = match.group(1)
            if token_name.startswith("ICON_"):
                icon_name = token_name[5:].lower().replace("_", "-")
                from src.ui.core.icon_manager import IconManager
                icon_color = tokens.get("COLOR_TEXT_PRIMARY", "#ffffff")
                return IconManager.get_icon_path(icon_name, color=icon_color)
            value = tokens.get(token_name)
            if value is None:
                logger.warning(f"[ThemeManager] Bilinmeyen token: @{token_name}")
                return match.group(0)
            return value

        resolved = re.sub(r"@([A-Z0-9_]+)", replace_token, qss_no_comments)

        for i, comment in enumerate(comments):
            resolved = resolved.replace(f"__COMMENT_{i}__", comment)

        return resolved

    @classmethod
    def connect_system_theme(cls, app: QApplication) -> None:
        """OS dark/light değişikliğini dinle. Qt 6.5+ gerektirir."""
        hints = app.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(cls._on_system_scheme_changed)
            logger.info("[ThemeManager] Sistem tema değişikliği dinleyicisi bağlandı.")
        else:
            logger.debug("[ThemeManager] colorSchemeChanged mevcut değil (Qt < 6.5).")

    @classmethod
    def _on_system_scheme_changed(cls, scheme) -> None:
        target = "dark" if scheme == Qt.ColorScheme.Dark else "light"
        if target != cls._current_theme_id:
            logger.info(f"[ThemeManager] OS tema değişti → '{target}'")
            cls.switch_theme(target)

    @classmethod
    def _load_inter_font(cls) -> str:
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
                logger.debug(f"[ThemeManager] Font bulunamadı: {path}")

        if loaded > 0:
            logger.info(f"[ThemeManager] Inter font yüklendi ({loaded}/{len(font_files)}).")
            return "Inter"
        logger.warning("[ThemeManager] Inter font bulunamadı, Segoe UI kullanılıyor.")
        return "Segoe UI"

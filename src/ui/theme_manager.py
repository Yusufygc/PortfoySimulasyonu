# src/ui/theme_manager.py
import os
import logging
from typing import Optional
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont, QFontDatabase

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

STYLE_MANIFEST: tuple[str, ...] = (
    "themes/{theme_name}.qss",
    "base/scrollbars.qss",
    "base/buttons.qss",
    "base/forms.qss",
    "base/tables.qss",
    "base/tabs.qss",
    "base/labels.qss",
    "base/groupboxes.qss",
    "base/checks.qss",
    "shared/navigation.qss",
    "shared/buttons.qss",
    "shared/forms.qss",
    "shared/containers.qss",
    "shared/dialogs.qss",
    "shared/cards.qss",
    "shared/tables.qss",
    "shared/lists.qss",
    "shared/trade_controls.qss",
    "features/dashboard.qss",
    "features/analysis.qss",
    "features/ai.qss",
    "features/optimization.qss",
    "features/planning.qss",
    "features/risk_profile.qss",
    "features/stock_detail.qss",
    "features/model_portfolio.qss",
    "features/watchlist.qss",
)

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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @classmethod
    def _do_apply(cls, theme_id: str, token_overrides: Optional[dict] = None) -> None:
        from src.ui.styles.tokens import DARK_THEME, LIGHT_THEME
        import src.ui.styles.tokens as _tokens_mod

        _token_map: dict[str, dict] = {
            "dark": DARK_THEME,
            "light": LIGHT_THEME,
        }
        tokens: dict[str, str] = {**_token_map.get(theme_id, DARK_THEME)}
        if token_overrides:
            tokens.update(token_overrides)

        # DEFAULT_THEME'i güncelle; IconManager token çözümlemesinde bunu kullanır.
        _tokens_mod.DEFAULT_THEME = tokens

        # Fontu yükle
        font_name = cls._load_inter_font()
        font = QFont(font_name, 10)
        font.setHintingPreference(QFont.PreferFullHinting)
        if cls._app:
            cls._app.setFont(font)

        # QSS oluştur ve uygula
        qss_name = THEME_REGISTRY[theme_id]["qss_name"]
        resolved_qss = cls._build_qss(qss_name, tokens)
        if resolved_qss and cls._app:
            try:
                cls._app.setStyleSheet(resolved_qss)
                logger.info(
                    f"[ThemeManager] Tema uygulandı: '{theme_id}' "
                    f"({len(tokens)} token, {len(STYLE_MANIFEST)} stil modülü)"
                )
            except Exception as e:
                logger.error(f"[ThemeManager] Stil uygulama hatası: {e}")

    @classmethod
    def _build_qss(cls, qss_name: str, tokens: dict[str, str]) -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        styles_dir = os.path.join(base_dir, "styles")

        combined_qss = ""
        for entry in STYLE_MANIFEST:
            file_name = entry.format(theme_name=qss_name)
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
                return IconManager.get_icon_path(icon_name, color="@COLOR_TEXT_PRIMARY")
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

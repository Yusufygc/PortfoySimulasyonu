from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.ui.theme_manager import THEME_REGISTRY, ThemeManager
from src.ui.widgets.shared import Toast


class AppearancePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme_card_widgets: dict[str, dict] = {}
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        card = QFrame()
        card.setProperty("cssClass", "panelFramePadded")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        title = QLabel("Tema Seçimi")
        title.setProperty("cssClass", "panelTitle")
        card_layout.addWidget(title)

        desc = QLabel(
            "Uygulamanın renk temasını seçin. Değişiklik anında uygulanır ve bir sonraki açılışta da korunur."
        )
        desc.setWordWrap(True)
        desc.setProperty("cssClass", "pageDescription")
        card_layout.addWidget(desc)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)

        for theme_id, theme_info in THEME_REGISTRY.items():
            card_frame, card_refs = self._build_theme_card(theme_id, theme_info)
            self._theme_card_widgets[theme_id] = card_refs
            cards_row.addWidget(card_frame)

        cards_row.addStretch()
        card_layout.addLayout(cards_row)
        card_layout.addStretch()

        layout.addWidget(card)
        layout.addStretch()
        self._refresh_theme_selection()

    def _build_theme_card(self, theme_id: str, theme_info: dict) -> tuple[QFrame, dict]:
        from src.ui.styles.tokens import DARK_THEME, LIGHT_THEME

        token_map = {"dark": DARK_THEME, "light": LIGHT_THEME}
        tok = token_map.get(theme_id, DARK_THEME)

        card = QFrame()
        card.setObjectName(f"themeCard_{theme_id}")
        card.setFixedWidth(230)
        card.setCursor(Qt.PointingHandCursor)
        card.mousePressEvent = lambda _event, tid=theme_id: self._on_theme_selected(tid)

        outer = QVBoxLayout(card)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        preview_frame = QFrame()
        preview_frame.setFixedHeight(60)
        preview_frame.setStyleSheet(
            f"background-color: {tok['COLOR_BG_BASE']}; border-radius: 8px 8px 0 0;"
        )
        preview_layout = QHBoxLayout(preview_frame)
        preview_layout.setContentsMargins(12, 10, 12, 10)
        preview_layout.setSpacing(6)

        for color in (
            tok["COLOR_SIDEBAR"],
            tok["COLOR_BG_SURFACE"],
            tok["COLOR_PRIMARY"],
            tok["COLOR_ACCENT"],
            tok["COLOR_SUCCESS"],
            tok["COLOR_DANGER"],
        ):
            swatch = QFrame()
            swatch.setFixedSize(20, 36)
            swatch.setStyleSheet(f"background-color: {color}; border-radius: 4px; border: none;")
            preview_layout.addWidget(swatch)
        preview_layout.addStretch()
        outer.addWidget(preview_frame)

        info_frame = QFrame()
        info_frame.setObjectName(f"themeCardInfo_{theme_id}")
        info_frame.setStyleSheet("border-radius: 0 0 8px 8px;")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(14, 12, 14, 14)
        info_layout.setSpacing(6)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)

        radio_lbl = QLabel("○")
        radio_lbl.setFixedWidth(18)
        name_row.addWidget(radio_lbl)

        name_lbl = QLabel(theme_info["display_name"])
        name_lbl.setProperty("cssClass", "panelTitle")
        name_row.addWidget(name_lbl)
        name_row.addStretch()

        status_lbl = QLabel("")
        status_lbl.setProperty("cssClass", "pageDescription")
        name_row.addWidget(status_lbl)

        info_layout.addLayout(name_row)

        desc_lbl = QLabel(theme_info["description"])
        desc_lbl.setWordWrap(True)
        desc_lbl.setProperty("cssClass", "pageDescription")
        info_layout.addWidget(desc_lbl)

        outer.addWidget(info_frame)
        refs = {"card": card, "radio": radio_lbl, "name": name_lbl, "status": status_lbl}
        return card, refs

    def _on_theme_selected(self, theme_id: str) -> None:
        if theme_id == ThemeManager.current_theme_id():
            return
        ThemeManager.switch_theme(theme_id)
        self._refresh_theme_selection()
        display = THEME_REGISTRY.get(theme_id, {}).get("display_name", theme_id)
        Toast.success(self, f"Tema değiştirildi: {display}")

    def _refresh_theme_selection(self) -> None:
        from src.ui.styles.tokens import DEFAULT_THEME

        current = ThemeManager.current_theme_id()
        primary = DEFAULT_THEME.get("COLOR_PRIMARY", "#3b82f6")
        border_def = DEFAULT_THEME.get("COLOR_BORDER", "#334155")
        bg_surface = DEFAULT_THEME.get("COLOR_BG_SURFACE", "#1e293b")
        text_pri = DEFAULT_THEME.get("COLOR_TEXT_PRIMARY", "#f1f5f9")
        text_sec = DEFAULT_THEME.get("COLOR_TEXT_SECONDARY", "#94a3b8")

        for theme_id, refs in self._theme_card_widgets.items():
            selected = theme_id == current
            card = refs["card"]
            radio = refs["radio"]
            name = refs["name"]
            stat = refs["status"]

            if selected:
                card.setStyleSheet(
                    f"QFrame#themeCard_{theme_id} {{"
                    f"  border: 2px solid {primary};"
                    f"  border-radius: 10px;"
                    f"  background-color: {bg_surface};"
                    f"}}"
                )
                radio.setText("●")
                radio.setStyleSheet(f"color: {primary}; font-size: 16px; background: transparent;")
                name.setStyleSheet(f"color: {primary}; background: transparent;")
                stat.setText("Aktif")
                stat.setStyleSheet(
                    f"color: {primary}; font-size: 11px;"
                    f" background-color: transparent;"
                    f" border: 1px solid {primary};"
                    f" border-radius: 4px; padding: 1px 6px;"
                )
                continue

            card.setStyleSheet(
                f"QFrame#themeCard_{theme_id} {{"
                f"  border: 1px solid {border_def};"
                f"  border-radius: 10px;"
                f"  background-color: {bg_surface};"
                f"}}"
            )
            radio.setText("○")
            radio.setStyleSheet(f"color: {text_sec}; font-size: 16px; background: transparent;")
            name.setStyleSheet(f"color: {text_pri}; background: transparent;")
            stat.setText("")
            stat.setStyleSheet("background: transparent; border: none;")

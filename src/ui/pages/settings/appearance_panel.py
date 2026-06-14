from __future__ import annotations
from src.ui.shared.locale_tr import L10N

from src.qt_compat.qtcore import Qt
from src.qt_compat.qtwidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.ui.theme_manager import THEME_REGISTRY, ThemeManager
from src.ui.widgets.shared import Toast


def _build_theme_preview_frame(tok) -> QFrame:
    # NOT: Bu inline setStyleSheet bilinçli olarak kaldı.
    # Önizleme başka temanın literal renk paletini boyar; aktif temadan bağımsız.
    preview_frame = QFrame()
    preview_frame.setFixedHeight(60)
    preview_frame.setStyleSheet(
        f"background-color: {tok['COLOR_BG_BASE']}; border-radius: 8px 8px 0 0;"
    )
    preview_layout = QHBoxLayout(preview_frame)
    preview_layout.setContentsMargins(12, 10, 12, 10)
    preview_layout.setSpacing(6)
    for color in (
        tok["COLOR_SIDEBAR"], tok["COLOR_BG_SURFACE"], tok["COLOR_PRIMARY"],
        tok["COLOR_ACCENT"], tok["COLOR_SUCCESS"], tok["COLOR_DANGER"],
    ):
        swatch = QFrame()
        swatch.setFixedSize(20, 36)
        swatch.setStyleSheet(f"background-color: {color}; border-radius: 4px; border: none;")
        preview_layout.addWidget(swatch)
    preview_layout.addStretch()
    return preview_frame


def _build_theme_info_frame(theme_id: str, theme_info: dict) -> tuple[QFrame, dict]:
    info_frame = QFrame()
    info_frame.setObjectName(f"themeCardInfo_{theme_id}")
    info_frame.setProperty("cssClass", "themeCardInfo")
    info_layout = QVBoxLayout(info_frame)
    info_layout.setContentsMargins(14, 12, 14, 14)
    info_layout.setSpacing(6)
    name_row = QHBoxLayout()
    name_row.setSpacing(8)
    radio_lbl = QLabel("○")
    radio_lbl.setFixedWidth(18)
    radio_lbl.setProperty("cssClass", "themeCardRadio")
    name_row.addWidget(radio_lbl)
    name_lbl = QLabel(theme_info["display_name"])
    name_lbl.setProperty("cssClass", "themeCardName")
    name_row.addWidget(name_lbl)
    name_row.addStretch()
    status_lbl = QLabel("")
    status_lbl.setProperty("cssClass", "themeCardStatus")
    name_row.addWidget(status_lbl)
    info_layout.addLayout(name_row)
    desc_lbl = QLabel(theme_info["description"])
    desc_lbl.setWordWrap(True)
    desc_lbl.setProperty("cssClass", "pageDescription")
    info_layout.addWidget(desc_lbl)
    return info_frame, {"radio": radio_lbl, "name": name_lbl, "status": status_lbl}


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

        title = QLabel(L10N.TEMA_SECIMI)
        title.setProperty("cssClass", "panelTitle")
        card_layout.addWidget(title)

        desc = QLabel(
            L10N.UYGULAMANIN_RENK_TEMASINI_SECIN_DEGISIKLIK
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
        card.setProperty("cssClass", "themeCard")
        card.setFixedWidth(230)
        card.setCursor(Qt.PointingHandCursor)
        card.mousePressEvent = lambda _event, tid=theme_id: self._on_theme_selected(tid)
        outer = QVBoxLayout(card)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(_build_theme_preview_frame(tok))
        info_frame, refs = _build_theme_info_frame(theme_id, theme_info)
        refs["card"] = card
        outer.addWidget(info_frame)
        return card, refs

    def _on_theme_selected(self, theme_id: str) -> None:
        if theme_id == ThemeManager.current_theme_id():
            return
        ThemeManager.switch_theme(theme_id)
        self._refresh_theme_selection()
        display = THEME_REGISTRY.get(theme_id, {}).get("display_name", theme_id)
        Toast.success(self, L10N.TEMA_DEGISTIRILDI_TMPL.format(display=display))

    def _refresh_theme_selection(self) -> None:
        """Seçili tema kartını QSS property'leri ile günceller.

        Qt, polish sonrası değişen property'leri otomatik re-eval etmez.
        Her widget için unpolish→polish çağrılarak QSS yeniden uygulanır.
        """
        current = ThemeManager.current_theme_id()

        for theme_id, refs in self._theme_card_widgets.items():
            selected = theme_id == current
            selected_str = "true" if selected else "false"

            card = refs["card"]
            radio = refs["radio"]
            name = refs["name"]
            stat = refs["status"]

            radio.setText("●" if selected else "○")
            stat.setText(L10N.AKTIF if selected else "")

            for w in (card, radio, name, stat):
                w.setProperty("selected", selected_str)
                self._repolish(w)

    @staticmethod
    def _repolish(widget) -> None:
        """QSS property değişiminden sonra widget'ı yeniden stillendirir.

        Qt'de setProperty() çağrısı polish'ten sonra yapılırsa QSS
        otomatik olarak yeniden hesaplanmaz. Unpolish→polish döngüsü
        zorla re-eval tetikler.
        """
        widget.style().unpolish(widget)
        widget.style().polish(widget)

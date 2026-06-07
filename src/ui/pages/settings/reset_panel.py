from __future__ import annotations
from src.ui.shared.confirm_dialog import ask_confirm
from src.ui.shared.locale_tr import L10N

from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget, QCheckBox, QComboBox
from PyQt5.QtCore import QSize

from src.ui.widgets.shared import AnimatedButton, Toast
from src.ui.core.icon_manager import IconManager


class ResetPanel(QWidget):
    def __init__(self, reset_service, settings=None, parent=None):
        super().__init__(parent)
        self.reset_service = reset_service
        from PyQt5.QtCore import QSettings
        self._settings = settings or QSettings("PortfoySimulasyonu", "PortfoySimulasyonu")
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        # ----------------------------------------------------
        # 1. Otomatik Fiyat Yenileme Kartı
        # ----------------------------------------------------
        refresh_card = QFrame()
        refresh_card.setProperty("cssClass", "panelFramePadded")
        refresh_layout = QVBoxLayout(refresh_card)
        refresh_layout.setContentsMargins(20, 20, 20, 20)
        refresh_layout.setSpacing(12)

        # Başlık ve İkon Satırı
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        icon_label = QLabel()
        icon_label.setPixmap(
            IconManager.get_icon("refresh-cw", color="@COLOR_ACCENT", size=QSize(20, 20)).pixmap(20, 20)
        )
        header_row.addWidget(icon_label)

        refresh_title = QLabel(L10N.OTOMATIK_FIYAT_YENILEME)
        refresh_title.setProperty("cssClass", "panelTitle")
        header_row.addWidget(refresh_title)
        header_row.addStretch()
        refresh_layout.addLayout(header_row)

        # Açıklama
        refresh_desc = QLabel(
            L10N.OTOMATIK_VERI_GUNCELLEME_ACIKLAMA
        )
        refresh_desc.setWordWrap(True)
        refresh_desc.setProperty("cssClass", "pageDescription")
        refresh_layout.addWidget(refresh_desc)

        # Seçenekler Satırı
        control_row = QHBoxLayout()
        control_row.setSpacing(10)

        self.chk_live_price_refresh = QCheckBox(L10N.OTOMATIK_FIYAT_YENILEME)
        self.chk_live_price_refresh.setChecked(self._live_price_refresh_enabled())
        self.chk_live_price_refresh.stateChanged.connect(self._on_live_price_refresh_settings_changed)

        control_row.addStretch()
        control_row.addWidget(self.chk_live_price_refresh)

        # Gizli combobox (Testler için)
        from src.ui.shared.live_price_refresh_controller import (
            DEFAULT_LIVE_PRICE_REFRESH_INTERVAL_MINUTES,
            LIVE_PRICE_REFRESH_INTERVAL_OPTIONS,
            LIVE_PRICE_REFRESH_ENABLED_KEY,
            LIVE_PRICE_REFRESH_INTERVAL_KEY,
        )
        self.combo_live_price_refresh_interval = QComboBox()
        self.combo_live_price_refresh_interval.setVisible(False)
        current_interval = self._live_price_refresh_interval()
        for minutes in LIVE_PRICE_REFRESH_INTERVAL_OPTIONS:
            self.combo_live_price_refresh_interval.addItem(f"{minutes} dk", minutes)
        selected_index = self.combo_live_price_refresh_interval.findData(current_interval)
        self.combo_live_price_refresh_interval.setCurrentIndex(max(0, selected_index))
        self.combo_live_price_refresh_interval.currentIndexChanged.connect(
            self._on_live_price_refresh_settings_changed
        )
        control_row.addWidget(self.combo_live_price_refresh_interval)
        refresh_layout.addLayout(control_row)

        layout.addWidget(refresh_card)

        # ----------------------------------------------------
        # 2. Sistem Sıfırlama Kartı
        # ----------------------------------------------------
        reset_card = QFrame()
        reset_card.setProperty("cssClass", "panelFramePadded")
        reset_layout = QVBoxLayout(reset_card)
        reset_layout.setContentsMargins(20, 20, 20, 20)
        reset_layout.setSpacing(12)

        # Başlık ve İkon Satırı
        reset_header = QHBoxLayout()
        reset_header.setSpacing(8)

        reset_icon_label = QLabel()
        reset_icon_label.setPixmap(
            IconManager.get_icon("trash-2", color="@COLOR_DANGER", size=QSize(20, 20)).pixmap(20, 20)
        )
        reset_header.addWidget(reset_icon_label)

        reset_title = QLabel(L10N.SISTEM_SIFIRLAMA)
        reset_title.setProperty("cssClass", "panelTitle")
        reset_header.addWidget(reset_title)
        reset_header.addStretch()
        reset_layout.addLayout(reset_header)

        reset_text = QLabel(
            L10N.TUM_PORTFOY_FIYAT_VE_HISSE +
            L10N.BU_ISLEM_GERI_ALINMAZ
        )
        reset_text.setWordWrap(True)
        reset_text.setProperty("cssClass", "pageDescription")
        reset_layout.addWidget(reset_text)

        action_row = QHBoxLayout()
        action_row.addStretch()

        self.btn_reset = AnimatedButton(L10N.SISTEMI_SIFIRLA)
        self.btn_reset.setIconName("trash-2", color="@COLOR_DANGER")
        self.btn_reset.setProperty("cssClass", "dangerTextButton")
        self.btn_reset.clicked.connect(self._on_reset)
        action_row.addWidget(self.btn_reset)

        reset_layout.addLayout(action_row)
        layout.addWidget(reset_card)
        layout.addStretch()

    def _live_price_refresh_enabled(self) -> bool:
        from src.ui.shared.live_price_refresh_controller import (
            DEFAULT_LIVE_PRICE_REFRESH_ENABLED,
            LIVE_PRICE_REFRESH_ENABLED_KEY,
        )
        value = self._settings.value(
            LIVE_PRICE_REFRESH_ENABLED_KEY,
            DEFAULT_LIVE_PRICE_REFRESH_ENABLED,
        )
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() not in {"0", "false", "hayir", "hayır", "no", "off"}
        return bool(value)

    def _live_price_refresh_interval(self) -> int:
        from src.ui.shared.live_price_refresh_controller import (
            DEFAULT_LIVE_PRICE_REFRESH_INTERVAL_MINUTES,
            LIVE_PRICE_REFRESH_INTERVAL_KEY,
            LIVE_PRICE_REFRESH_INTERVAL_OPTIONS,
        )
        value = self._settings.value(
            LIVE_PRICE_REFRESH_INTERVAL_KEY,
            DEFAULT_LIVE_PRICE_REFRESH_INTERVAL_MINUTES,
        )
        try:
            minutes = int(value)
        except (TypeError, ValueError):
            minutes = DEFAULT_LIVE_PRICE_REFRESH_INTERVAL_MINUTES
        return minutes if minutes in LIVE_PRICE_REFRESH_INTERVAL_OPTIONS else DEFAULT_LIVE_PRICE_REFRESH_INTERVAL_MINUTES

    def _on_live_price_refresh_settings_changed(self) -> None:
        from src.ui.shared.live_price_refresh_controller import (
            LIVE_PRICE_REFRESH_ENABLED_KEY,
            LIVE_PRICE_REFRESH_INTERVAL_KEY,
            DEFAULT_LIVE_PRICE_REFRESH_INTERVAL_MINUTES,
        )
        self._settings.setValue(LIVE_PRICE_REFRESH_ENABLED_KEY, self.chk_live_price_refresh.isChecked())
        self._settings.setValue(
            LIVE_PRICE_REFRESH_INTERVAL_KEY,
            self.combo_live_price_refresh_interval.currentData() or DEFAULT_LIVE_PRICE_REFRESH_INTERVAL_MINUTES,
        )
        self._settings.sync()
        window = self.window()
        if hasattr(window, "reload_live_price_refresh_settings"):
            window.reload_live_price_refresh_settings()

    def _on_reset(self) -> None:
        if not ask_confirm(
            self,
            L10N.PORTFOYU_SIFIRLA,
            L10N.TUM_VERILER_SILINECEK_EMIN_MISINIZ,
        ):
            return

        try:
            self.reset_service.reset_all()
            Toast.success(self, L10N.SISTEM_BASARIYLA_SIFIRLANDI)
        except Exception as exc:
            Toast.error(self, L10N.SISTEM_SIFIRLANAMADI_TMPL.format(exc=exc))

from __future__ import annotations

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout

from .base_page import BasePage
from src.ui.core.icon_manager import IconManager
from src.ui.widgets.shared import AnimatedButton, Toast


class SettingsPage(BasePage):
    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container
        self.page_title = "Ayarlar"
        self.reset_service = container.reset_service
        self._init_ui()

    def _init_ui(self):
        header = QHBoxLayout()
        header.setSpacing(10)

        icon_label = QLabel()
        icon_label.setPixmap(
            IconManager.get_icon("save", color="@COLOR_ACCENT", size=QSize(28, 28)).pixmap(28, 28)
        )
        header.addWidget(icon_label)

        title_label = QLabel("Ayarlar")
        title_label.setProperty("cssClass", "pageTitle")
        header.addWidget(title_label)
        header.addStretch()
        self.main_layout.addLayout(header)

        description = QLabel(
            "Uygulama genel aksiyonlarini buradan yonetin. "
            "Tehlikeli ve sistem seviyesindeki islemler dashboard yerine bu sayfada tutulur."
        )
        description.setWordWrap(True)
        description.setProperty("cssClass", "pageDescription")
        self.main_layout.addWidget(description)

        reset_card = QFrame()
        reset_card.setProperty("cssClass", "panelFramePadded")
        reset_layout = QVBoxLayout(reset_card)
        reset_layout.setContentsMargins(20, 20, 20, 20)
        reset_layout.setSpacing(12)

        reset_title = QLabel("Sistem Sifirlama")
        reset_title.setProperty("cssClass", "panelTitle")
        reset_layout.addWidget(reset_title)

        reset_text = QLabel(
            "Tum portfoy, fiyat ve hisse verilerini siler. "
            "Bu islem geri alinmaz."
        )
        reset_text.setWordWrap(True)
        reset_text.setProperty("cssClass", "pageDescription")
        reset_layout.addWidget(reset_text)

        action_row = QHBoxLayout()
        action_row.addStretch()

        self.btn_reset = AnimatedButton(" Sistemi Sifirla")
        self.btn_reset.setIconName("trash-2", color="@COLOR_DANGER")
        self.btn_reset.setProperty("cssClass", "dangerTextButton")
        self.btn_reset.clicked.connect(self._on_reset)
        action_row.addWidget(self.btn_reset)

        reset_layout.addLayout(action_row)
        self.main_layout.addWidget(reset_card)
        self.main_layout.addStretch()

    def _on_reset(self):
        reply = QMessageBox.question(
            self,
            "Portfoyu Sifirla",
            "TUM veriler silinecek. Emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self.reset_service.reset_all()
            Toast.success(self, "Sistem basariyla sifirlandi.")
        except Exception as exc:
            Toast.error(self, f"Sistem sifirlanamadi: {exc}")

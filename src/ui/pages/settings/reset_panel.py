from __future__ import annotations

from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget

from src.ui.widgets.shared import AnimatedButton, Toast


class ResetPanel(QWidget):
    def __init__(self, reset_service, parent=None):
        super().__init__(parent)
        self.reset_service = reset_service
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        reset_card = QFrame()
        reset_card.setProperty("cssClass", "panelFramePadded")
        reset_layout = QVBoxLayout(reset_card)
        reset_layout.setContentsMargins(20, 20, 20, 20)
        reset_layout.setSpacing(12)

        reset_title = QLabel("Sistem Sıfırlama")
        reset_title.setProperty("cssClass", "panelTitle")
        reset_layout.addWidget(reset_title)

        reset_text = QLabel(
            "Tüm portföy, fiyat ve hisse verilerini siler. "
            "Bu işlem geri alınmaz."
        )
        reset_text.setWordWrap(True)
        reset_text.setProperty("cssClass", "pageDescription")
        reset_layout.addWidget(reset_text)

        action_row = QHBoxLayout()
        action_row.addStretch()

        self.btn_reset = AnimatedButton(" Sistemi Sıfırla")
        self.btn_reset.setIconName("trash-2", color="@COLOR_DANGER")
        self.btn_reset.setProperty("cssClass", "dangerTextButton")
        self.btn_reset.clicked.connect(self._on_reset)
        action_row.addWidget(self.btn_reset)

        reset_layout.addLayout(action_row)
        layout.addWidget(reset_card)
        layout.addStretch()

    def _on_reset(self) -> None:
        reply = QMessageBox.question(
            self,
            "Portföyü Sıfırla",
            "TÜM veriler silinecek. Emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self.reset_service.reset_all()
            Toast.success(self, "Sistem başarıyla sıfırlandı.")
        except Exception as exc:
            Toast.error(self, f"Sistem sıfırlanamadı: {exc}")

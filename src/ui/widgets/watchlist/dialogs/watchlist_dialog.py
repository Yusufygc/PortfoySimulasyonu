from typing import Optional, Tuple
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFormLayout
from PyQt5.QtCore import Qt

class WatchlistDialog(QDialog):
    """Liste oluşturma ve düzenleme diyaloğu."""

    def __init__(self, title: str, name: str = "", description: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(True)
        self.resize(350, 180)
        self.setProperty("cssClass", "dialogContainer")

        self.name_input = QLineEdit(name)
        self.name_input.setPlaceholderText("Liste adı")
        self.name_input.setProperty("cssClass", "tradeInputNormal")

        self.desc_input = QLineEdit(description)
        self.desc_input.setPlaceholderText("Açıklama (opsiyonel)")
        self.desc_input.setProperty("cssClass", "tradeInputNormal")

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        form = QFormLayout()
        form.setSpacing(10)
        
        lbl_name = QLabel("Liste Adı:")
        lbl_name.setProperty("cssClass", "formLabel")
        form.addRow(lbl_name, self.name_input)

        lbl_desc = QLabel("Açıklama:")
        lbl_desc.setProperty("cssClass", "formLabel")
        form.addRow(lbl_desc, self.desc_input)

        layout.addLayout(form)

        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("İptal")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setProperty("cssClass", "secondaryButton")

        btn_confirm = QPushButton("Kaydet")
        btn_confirm.clicked.connect(self.accept)
        btn_confirm.setProperty("cssClass", "primaryButton")
        btn_confirm.setDefault(True)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_confirm)
        layout.addLayout(btn_layout)

    def get_data(self) -> Optional[Tuple[str, str]]:
        if not self.name_input.text().strip():
            return None
        return (self.name_input.text().strip(), self.desc_input.text().strip())

    @classmethod
    def get_watchlist_data(cls, parent, title: str, name: str = "", description: str = "") -> Optional[Tuple[str, str]]:
        dialog = cls(title, name, description, parent)
        if dialog.exec_() == QDialog.Accepted:
            return dialog.get_data()
        return None

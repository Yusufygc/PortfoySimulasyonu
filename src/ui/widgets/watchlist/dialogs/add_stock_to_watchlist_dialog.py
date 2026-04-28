from __future__ import annotations

from typing import Optional, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class AddStockToWatchlistDialog(QDialog):
    """Takip listesine hisse eklemek icin tek adimli form dialogu."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Hisse Ekle")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setProperty("cssClass", "dialogContainer")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        title = QLabel("Listeye eklenecek hisse bilgilerini girin.")
        title.setProperty("cssClass", "dialogSubtitle")
        title.setWordWrap(True)
        main_layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)

        self.ticker_edit = QLineEdit()
        self.ticker_edit.setPlaceholderText("Örn: ASELS veya ASELS.IS")
        self.ticker_edit.setProperty("cssClass", "tradeInputNormal")
        self.ticker_edit.setClearButtonEnabled(True)

        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Opsiyonel")
        self.notes_edit.setProperty("cssClass", "tradeInputNormal")
        self.notes_edit.setClearButtonEnabled(True)

        ticker_label = QLabel("Hisse ticker'ı:")
        ticker_label.setProperty("cssClass", "formLabel")
        notes_label = QLabel("Not:")
        notes_label.setProperty("cssClass", "formLabel")

        form.addRow(ticker_label, self.ticker_edit)
        form.addRow(notes_label, self.notes_edit)
        main_layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_ok = QPushButton("Ekle")
        self.btn_ok.setProperty("cssClass", "primaryButton")
        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.setProperty("cssClass", "secondaryButton")

        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)

        self.btn_ok.clicked.connect(self._on_accept_clicked)
        self.btn_cancel.clicked.connect(self.reject)
        self.ticker_edit.returnPressed.connect(self._on_accept_clicked)

    def values(self) -> Tuple[str, Optional[str]]:
        ticker = self.ticker_edit.text().strip()
        notes = self.notes_edit.text().strip()
        return ticker, notes or None

    @staticmethod
    def get_stock_input(parent=None) -> Optional[Tuple[str, Optional[str]]]:
        dialog = AddStockToWatchlistDialog(parent)
        if dialog.exec_() != QDialog.Accepted:
            return None
        return dialog.values()

    def _on_accept_clicked(self) -> None:
        ticker = self.ticker_edit.text().strip()
        if not ticker:
            QMessageBox.warning(self, "Eksik Bilgi", "Hisse ticker'ı boş olamaz.")
            self.ticker_edit.setFocus()
            return

        self.accept()

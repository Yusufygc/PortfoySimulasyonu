from __future__ import annotations
from src.ui.shared.locale_tr import L10N

from typing import Optional
from src.qt_compat.qtcore import Qt
from src.qt_compat.qtwidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)
from src.ui.widgets.dialog_behavior import configure_dialog_behavior


class EditStockInWatchlistDialog(QDialog):
    """Takip listesindeki hisse notunu düzenlemek için form dialogu."""

    def __init__(self, ticker: str, current_notes: Optional[str] = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(L10N.HISSE_NOTUNU_DUZENLE)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowCloseButtonHint, True)
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setProperty("cssClass", "dialogContainer")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        title = QLabel(f"{L10N.HISSE_1}: {ticker}")
        title.setProperty("cssClass", "dialogSubtitle")
        title.setWordWrap(True)
        main_layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)

        self.notes_edit = QLineEdit()
        self.notes_edit.setMaxLength(100)
        if current_notes:
            self.notes_edit.setText(current_notes)
        self.notes_edit.setPlaceholderText(L10N.OPSIYONEL)
        self.notes_edit.setProperty("cssClass", "tradeInputNormal")
        self.notes_edit.setClearButtonEnabled(True)

        notes_label = QLabel(L10N.HISSE_NOTU)
        notes_label.setProperty("cssClass", "formLabel")

        form.addRow(notes_label, self.notes_edit)
        main_layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_ok = QPushButton(L10N.SAVE)
        self.btn_ok.setProperty("cssClass", "primaryButton")
        self.btn_ok.setDefault(True)
        self.btn_cancel = QPushButton(L10N.CANCEL)
        self.btn_cancel.setProperty("cssClass", "secondaryButton")

        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)

        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        configure_dialog_behavior(self, self.btn_ok)

    def values(self) -> Optional[str]:
        notes = self.notes_edit.text().strip()
        return notes or None

    @staticmethod
    def get_notes_input(ticker: str, current_notes: Optional[str] = None, parent=None) -> tuple[bool, Optional[str]]:
        dialog = EditStockInWatchlistDialog(ticker, current_notes, parent)
        if dialog.exec() != QDialog.Accepted:
            return False, None
        return True, dialog.values()

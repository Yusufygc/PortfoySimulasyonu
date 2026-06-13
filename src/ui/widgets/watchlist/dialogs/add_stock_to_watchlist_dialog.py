from __future__ import annotations
from src.ui.shared.locale_tr import L10N

from typing import Optional, Tuple

from src.qt_compat.qtcore import Qt
from src.qt_compat.qtwidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from src.ui.widgets.dialog_behavior import configure_dialog_behavior
from src.ui.shared.ticker_validation import is_valid_ticker_input


class AddStockToWatchlistDialog(QDialog):
    """Takip listesine hisse eklemek icin tek adimli form dialogu."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(L10N.HISSE_EKLE_1)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowCloseButtonHint, True)
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setProperty("cssClass", "dialogContainer")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        title = QLabel(L10N.LISTEYE_EKLENECEK_HISSE_BILGILERINI_GIRIN)
        title.setProperty("cssClass", "dialogSubtitle")
        title.setWordWrap(True)
        main_layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)

        self.ticker_edit = QLineEdit()
        self.ticker_edit.setMaxLength(15)
        self.ticker_edit.setPlaceholderText(L10N.ORN_ASELS_VEYA_ASELSIS)
        self.ticker_edit.setProperty("cssClass", "tradeInputNormal")
        self.ticker_edit.setClearButtonEnabled(True)

        self.notes_edit = QLineEdit()
        self.notes_edit.setMaxLength(100)
        self.notes_edit.setPlaceholderText(L10N.OPSIYONEL)
        self.notes_edit.setProperty("cssClass", "tradeInputNormal")
        self.notes_edit.setClearButtonEnabled(True)

        ticker_label = QLabel(L10N.HISSE_2)
        ticker_label.setProperty("cssClass", "formLabel")
        notes_label = QLabel(L10N.NOT)
        notes_label.setProperty("cssClass", "formLabel")

        form.addRow(ticker_label, self.ticker_edit)
        form.addRow(notes_label, self.notes_edit)
        main_layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_ok = QPushButton(L10N.EKLE)
        self.btn_ok.setProperty("cssClass", "primaryButton")
        self.btn_ok.setDefault(True)
        self.btn_cancel = QPushButton(L10N.CANCEL)
        self.btn_cancel.setProperty("cssClass", "secondaryButton")

        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)

        self.btn_ok.clicked.connect(self._on_accept_clicked)
        self.btn_cancel.clicked.connect(self.reject)
        self.ticker_edit.returnPressed.connect(self._on_accept_clicked)
        configure_dialog_behavior(self, self.btn_ok, self._on_accept_clicked)

    def values(self) -> Tuple[str, Optional[str]]:
        ticker = self.ticker_edit.text().strip()
        notes = self.notes_edit.text().strip()
        return ticker, notes or None

    @staticmethod
    def get_stock_input(parent=None) -> Optional[Tuple[str, Optional[str]]]:
        dialog = AddStockToWatchlistDialog(parent)
        if dialog.exec() != QDialog.Accepted:
            return None
        return dialog.values()

    def _on_accept_clicked(self) -> None:
        ticker = self.ticker_edit.text().strip()
        if not ticker:
            QMessageBox.warning(self, L10N.EKSIK_BILGI, L10N.HISSE_BOS_OLAMAZ)
            self.ticker_edit.setFocus()
            return
        if not is_valid_ticker_input(ticker):
            QMessageBox.warning(self, L10N.ERROR, L10N.GECERSIZ_HISSE_KODU)
            self.ticker_edit.setFocus()
            return

        self.accept()

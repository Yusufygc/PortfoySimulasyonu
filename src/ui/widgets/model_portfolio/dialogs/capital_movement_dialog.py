from __future__ import annotations
from src.ui.shared.locale_tr import L10N

from decimal import Decimal
from typing import Optional

from src.qt_compat.qtcore import QDate, QTime, Qt
from src.qt_compat.qtwidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
)

from src.ui.widgets.shared import CurrencySpinBox
from src.ui.widgets.dialog_behavior import configure_dialog_behavior


class CapitalMovementDialog(QDialog):
    def __init__(self, current_cash: Decimal, net_capital: Decimal, parent=None):
        super().__init__(parent)
        self.current_cash = current_cash
        self.net_capital = net_capital
        self.setWindowTitle(L10N.SERMAYE_YONETIMI_1)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowCloseButtonHint, True)
        self.setModal(True)
        self.setProperty("cssClass", "tradeDialog")
        self.resize(420, 330)
        self._init_ui()
        configure_dialog_behavior(self, self.btn_confirm, self.accept)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        lbl_info = QLabel(f"Nakit: TL {self.current_cash:,.2f}   Net Sermaye: TL {self.net_capital:,.2f}")
        lbl_info.setProperty("cssClass", "dialogHeaderTitle")
        layout.addWidget(lbl_info)

        form = QFormLayout()
        form.setSpacing(12)

        self.combo_action = QComboBox()
        self.combo_action.addItem(L10N.SERMAYE_EKLE, "DEPOSIT")
        self.combo_action.addItem(L10N.SERMAYE_CEK, "WITHDRAW")
        self.combo_action.setProperty("cssClass", "tradeInputNormal")
        form.addRow("İşlem:", self.combo_action)

        self.spin_amount = CurrencySpinBox()
        self.spin_amount.setRange(0.01, 100_000_000)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setGroupSeparatorShown(True)
        self.spin_amount.setSuffix(" TL")
        self.spin_amount.setValue(10_000)
        self.spin_amount.setProperty("cssClass", "tradeInputNormal")
        form.addRow(L10N.TUTAR_1, self.spin_amount)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setProperty("cssClass", "tradeInputNormal")
        form.addRow(L10N.TARIH_1, self.date_edit)

        self.time_edit = QTimeEdit(QTime.currentTime())
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setProperty("cssClass", "tradeInputNormal")
        form.addRow("Saat:", self.time_edit)

        self.txt_notes = QLineEdit()
        self.txt_notes.setPlaceholderText(L10N.OPSIYONEL)
        self.txt_notes.setProperty("cssClass", "tradeInputNormal")
        form.addRow(L10N.NOT, self.txt_notes)

        layout.addLayout(form)

        button_row = QHBoxLayout()
        button_row.addStretch()
        btn_cancel = QPushButton(L10N.CANCEL)
        btn_cancel.setProperty("cssClass", "secondaryButton")
        btn_cancel.clicked.connect(self.reject)

        self.btn_confirm = QPushButton(L10N.SAVE)
        self.btn_confirm.setProperty("cssClass", "successButton")
        self.btn_confirm.clicked.connect(self.accept)
        self.btn_confirm.setDefault(True)

        button_row.addWidget(btn_cancel)
        button_row.addWidget(self.btn_confirm)
        layout.addLayout(button_row)

    def get_result(self) -> Optional[dict]:
        if not self.spin_amount.has_valid_input(require_positive=True):
            return None
        amount = self.spin_amount.input_decimal_value()
        return {
            "movement_type": self.combo_action.currentData(),
            "amount": amount,
            "movement_date": self.date_edit.date().toPyDate(),
            "movement_time": self.time_edit.time().toPyTime(),
            "notes": self.txt_notes.text().strip() or None,
        }

    def accept(self) -> None:
        if not self.spin_amount.has_valid_input(require_positive=True):
            QMessageBox.warning(self, L10N.ERROR, L10N.GECERLI_BIR_TUTAR_GIRINIZ)
            self.spin_amount.setFocus()
            return
        super().accept()

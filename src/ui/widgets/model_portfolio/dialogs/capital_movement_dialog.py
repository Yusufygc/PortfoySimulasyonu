from __future__ import annotations

from decimal import Decimal
from typing import Optional

from PyQt5.QtCore import QDate, QTime, Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
)

from src.ui.widgets.dialog_behavior import configure_dialog_behavior


class CapitalMovementDialog(QDialog):
    def __init__(self, current_cash: Decimal, net_capital: Decimal, parent=None):
        super().__init__(parent)
        self.current_cash = current_cash
        self.net_capital = net_capital
        self.setWindowTitle("Sermaye Yönetimi")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
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
        self.combo_action.addItem("Sermaye Ekle", "DEPOSIT")
        self.combo_action.addItem("Sermaye Çek", "WITHDRAW")
        self.combo_action.setProperty("cssClass", "tradeInputNormal")
        form.addRow("İşlem:", self.combo_action)

        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(0.01, 100_000_000)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setGroupSeparatorShown(True)
        self.spin_amount.setSuffix(" TL")
        self.spin_amount.setValue(10_000)
        self.spin_amount.setProperty("cssClass", "tradeInputNormal")
        form.addRow("Tutar:", self.spin_amount)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setProperty("cssClass", "tradeInputNormal")
        form.addRow("Tarih:", self.date_edit)

        self.time_edit = QTimeEdit(QTime.currentTime())
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setProperty("cssClass", "tradeInputNormal")
        form.addRow("Saat:", self.time_edit)

        self.txt_notes = QLineEdit()
        self.txt_notes.setPlaceholderText("Opsiyonel")
        self.txt_notes.setProperty("cssClass", "tradeInputNormal")
        form.addRow("Not:", self.txt_notes)

        layout.addLayout(form)

        button_row = QHBoxLayout()
        button_row.addStretch()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setProperty("cssClass", "secondaryButton")
        btn_cancel.clicked.connect(self.reject)

        self.btn_confirm = QPushButton("Kaydet")
        self.btn_confirm.setProperty("cssClass", "successButton")
        self.btn_confirm.clicked.connect(self.accept)
        self.btn_confirm.setDefault(True)

        button_row.addWidget(btn_cancel)
        button_row.addWidget(self.btn_confirm)
        layout.addLayout(button_row)

    def get_result(self) -> Optional[dict]:
        amount = Decimal(str(self.spin_amount.value()))
        if amount <= 0:
            return None
        return {
            "movement_type": self.combo_action.currentData(),
            "amount": amount,
            "movement_date": self.date_edit.date().toPyDate(),
            "movement_time": self.time_edit.time().toPyTime(),
            "notes": self.txt_notes.text().strip() or None,
        }

from typing import Optional, Dict
from decimal import Decimal

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFormLayout,
    QComboBox,
    QDoubleSpinBox,
    QPushButton,
    QDateEdit,
    QTimeEdit,
    QLineEdit,
)
from PyQt5.QtCore import Qt, QDate, QTime

from src.ui.widgets.dialog_behavior import configure_dialog_behavior

class CapitalDialog(QDialog):
    """Sermaye ekleme/çekme diyaloğu."""

    def __init__(self, current_capital: Decimal, parent=None):
        super().__init__(parent)
        self.current_capital = current_capital
        
        self.setWindowTitle("Sermaye Yönetimi")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.resize(350, 300)
        self.setModal(True)
        self.setProperty("cssClass", "dialogContainer")
        
        self._init_ui()
        configure_dialog_behavior(self, self.btn_confirm, self.accept)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Mevcut sermaye
        lbl_current = QLabel(f"Mevcut Sermaye: ₺{self.current_capital:,.2f}")
        lbl_current.setProperty("cssClass", "dialogHeaderTitle")
        layout.addWidget(lbl_current)
        
        form = QFormLayout()
        form.setSpacing(10)
        
        # İşlem türü
        self.combo_action = QComboBox()
        self.combo_action.addItems(["Sermaye Ekle", "Sermaye Çek"])
        self.combo_action.setProperty("cssClass", "tradeInputNormal")
        form.addRow("İşlem:", self.combo_action)
        
        # Tutar
        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(0.01, 100000000)
        self.spin_amount.setValue(10000)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setGroupSeparatorShown(True)
        self.spin_amount.setSuffix(" TL")
        self.spin_amount.setProperty("cssClass", "tradeInputNormal")
        form.addRow("Tutar:", self.spin_amount)
        
        # Tarih
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setProperty("cssClass", "tradeInputNormal")
        form.addRow("Tarih:", self.date_edit)
        
        # Saat
        self.time_edit = QTimeEdit(QTime.currentTime())
        self.time_edit.setProperty("cssClass", "tradeInputNormal")
        form.addRow("Saat:", self.time_edit)
        
        # Not
        self.txt_notes = QLineEdit()
        self.txt_notes.setPlaceholderText("Opsiyonel")
        self.txt_notes.setProperty("cssClass", "tradeInputNormal")
        form.addRow("Not:", self.txt_notes)
        
        layout.addLayout(form)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setProperty("cssClass", "secondaryButton")
        
        self.btn_confirm = QPushButton("Onayla")
        self.btn_confirm.clicked.connect(self.accept)
        self.btn_confirm.setProperty("cssClass", "tradeConfirmBuyBtn")
        self.btn_confirm.setDefault(True)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_confirm)
        layout.addLayout(btn_layout)

    def get_result(self) -> Optional[Dict]:
        action = "deposit" if self.combo_action.currentIndex() == 0 else "withdraw"
        amount = Decimal(str(self.spin_amount.value()))
        
        if amount <= 0:
            return None
        
        return {
            "action": action,
            "amount": amount,
            "movement_date": self.date_edit.date().toPyDate(),
            "movement_time": self.time_edit.time().toPyTime(),
            "notes": self.txt_notes.text().strip() or None,
        }

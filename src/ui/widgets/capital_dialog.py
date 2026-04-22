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
)

class CapitalDialog(QDialog):
    """Sermaye ekleme/çekme diyaloğu."""

    def __init__(self, current_capital: Decimal, parent=None):
        super().__init__(parent)
        self.current_capital = current_capital
        
        self.setWindowTitle("Sermaye Yönetimi")
        self.resize(350, 200)
        self.setModal(True)
        self.setProperty("cssClass", "dialogContainer")
        
        self._init_ui()

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
        self.spin_amount.setSuffix(" TL")
        self.spin_amount.setProperty("cssClass", "tradeInputNormal")
        form.addRow("Tutar:", self.spin_amount)
        
        layout.addLayout(form)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setProperty("cssClass", "secondaryButton")
        
        btn_confirm = QPushButton("Onayla")
        btn_confirm.clicked.connect(self.accept)
        btn_confirm.setProperty("cssClass", "tradeConfirmBuyBtn")
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_confirm)
        layout.addLayout(btn_layout)

    def get_result(self) -> Optional[Dict]:
        action = "deposit" if self.combo_action.currentIndex() == 0 else "withdraw"
        amount = Decimal(str(self.spin_amount.value()))
        
        if amount <= 0:
            return None
        
        return {
            "action": action,
            "amount": amount,
        }

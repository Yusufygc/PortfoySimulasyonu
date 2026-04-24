from __future__ import annotations

from decimal import Decimal
from typing import Optional

from PyQt5.QtWidgets import QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout


class PortfolioInputDialog(QDialog):
    def __init__(self, parent=None, portfolio=None):
        super().__init__(parent)
        self.portfolio = portfolio
        self.is_edit = portfolio is not None
        self.setWindowTitle("Portfoy Duzenle" if self.is_edit else "Yeni Portfoy")
        self.resize(400, 200)
        self.setModal(True)
        self.setProperty("cssClass", "tradeDialog")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_name = QLineEdit(self.portfolio.name if self.is_edit else "")
        form.addRow("Adi:", self.txt_name)

        self.txt_desc = QLineEdit((self.portfolio.description or "") if self.is_edit else "")
        form.addRow("Aciklama:", self.txt_desc)

        self.spin_cash = QDoubleSpinBox()
        self.spin_cash.setRange(1000, 100_000_000)
        self.spin_cash.setDecimals(2)
        self.spin_cash.setSuffix(" TL")
        self.spin_cash.setValue(float(self.portfolio.initial_cash) if self.is_edit else 100_000)
        form.addRow("Sermaye:", self.spin_cash)

        layout.addLayout(form)

        button_row = QHBoxLayout()
        button_row.addStretch()
        btn_cancel = QPushButton("Iptal")
        btn_cancel.setProperty("cssClass", "secondaryButton")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Kaydet")
        btn_save.setProperty("cssClass", "successButton")
        btn_save.clicked.connect(self.accept)
        button_row.addWidget(btn_cancel)
        button_row.addWidget(btn_save)
        layout.addLayout(button_row)

    def get_result(self) -> Optional[dict]:
        name = self.txt_name.text().strip()
        if not name:
            return None
        return {
            "name": name,
            "description": self.txt_desc.text().strip() or None,
            "initial_cash": Decimal(str(self.spin_cash.value())),
        }


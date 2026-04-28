from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import (
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

logger = logging.getLogger(__name__)


class TradeInputDialog(QDialog):
    def __init__(self, side: str, price_lookup_func=None, parent=None):
        super().__init__(parent)
        self.side = side
        self.price_lookup_func = price_lookup_func
        self.setWindowTitle("Hisse Al" if side == "BUY" else "Hisse Sat")
        self.setFixedSize(450, 320)
        self.setModal(True)
        self.setProperty("cssClass", "tradeDialog")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        form = QFormLayout()
        form.setSpacing(15)
        form.setLabelAlignment(Qt.AlignLeft)

        self.txt_ticker = QLineEdit()
        self.txt_ticker.setPlaceholderText("Orn: ASELS")
        self.txt_ticker.setMinimumHeight(45)
        self.txt_ticker.returnPressed.connect(self._on_lookup)
        form.addRow("Ticker:", self.txt_ticker)

        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 1_000_000)
        self.spin_qty.setValue(100)
        self.spin_qty.setMinimumHeight(45)
        form.addRow("Lot:", self.spin_qty)

        price_row = QHBoxLayout()
        self.spin_price = QDoubleSpinBox()
        self.spin_price.setRange(0.01, 100_000)
        self.spin_price.setDecimals(2)
        self.spin_price.setSuffix(" TL")
        self.spin_price.setMinimumWidth(180)
        self.spin_price.setMinimumHeight(45)
        price_row.addWidget(self.spin_price)

        btn_lookup = QPushButton("Fiyat Al")
        btn_lookup.setCursor(Qt.PointingHandCursor)
        btn_lookup.setProperty("cssClass", "primaryButton")
        btn_lookup.setMinimumHeight(45)
        btn_lookup.clicked.connect(self._on_lookup)
        price_row.addWidget(btn_lookup)
        form.addRow("Fiyat:", price_row)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setMinimumHeight(45)
        form.addRow("Tarih:", self.date_edit)

        layout.addLayout(form)
        layout.addStretch()

        button_row = QHBoxLayout()
        button_row.addStretch()
        btn_cancel = QPushButton("Iptal")
        btn_cancel.setMinimumHeight(40)
        btn_cancel.setProperty("cssClass", "secondaryButton")
        btn_cancel.clicked.connect(self.reject)

        btn_action = QPushButton("Al" if self.side == "BUY" else "Sat")
        btn_action.setMinimumHeight(40)
        btn_action.setProperty("cssClass", "successButton" if self.side == "BUY" else "dangerButton")
        btn_action.clicked.connect(self.accept)

        button_row.addWidget(btn_cancel)
        button_row.addWidget(btn_action)
        layout.addLayout(button_row)

    def _on_lookup(self):
        if not self.price_lookup_func:
            return
        ticker = self.txt_ticker.text().strip()
        if not ticker:
            return
        try:
            result = self.price_lookup_func(ticker)
            if result:
                self.spin_price.setValue(float(result.price))
        except Exception as exc:
            logger.warning("Fiyat sorgulama basarisiz (%s): %s", ticker, exc)

    def get_result(self) -> Optional[dict]:
        ticker = self.txt_ticker.text().strip()
        if not ticker:
            return None
        return {
            "ticker": ticker.upper(),
            "quantity": self.spin_qty.value(),
            "price": Decimal(str(self.spin_price.value())),
            "trade_date": self.date_edit.date().toPyDate(),
        }


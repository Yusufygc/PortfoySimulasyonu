from __future__ import annotations
from src.ui.shared.locale_tr import L10N

import logging
from decimal import Decimal
from typing import Optional

from PyQt5.QtCore import QDate, QTime, Qt
from PyQt5.QtWidgets import (
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
)

from src.ui.widgets.shared import CurrencySpinBox
from src.ui.widgets.dialog_behavior import configure_dialog_behavior

logger = logging.getLogger(__name__)


class TradeInputDialog(QDialog):
    def __init__(self, side: str, price_lookup_func=None, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.side = side
        self.price_lookup_func = price_lookup_func
        self.setWindowTitle(L10N.HISSE_AL_1 if side == "BUY" else L10N.HISSE_SAT_1)
        self.setFixedSize(450, 425)
        self.setModal(True)
        self.setProperty("cssClass", "tradeDialog")
        self._init_ui()
        configure_dialog_behavior(self, self.btn_action, self._on_enter_pressed)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        form = QFormLayout()
        form.setSpacing(15)
        form.setLabelAlignment(Qt.AlignLeft)

        self.txt_ticker = QLineEdit()
        self.txt_ticker.setPlaceholderText(L10N.ORN_ASELS)
        self.txt_ticker.setMinimumHeight(45)
        self.txt_ticker.returnPressed.connect(self._on_lookup)
        form.addRow("Ticker:", self.txt_ticker)

        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 1_000_000)
        self.spin_qty.setValue(100)
        self.spin_qty.setMinimumHeight(45)
        form.addRow("Lot:", self.spin_qty)

        price_row = QHBoxLayout()
        self.spin_price = CurrencySpinBox()
        self.spin_price.setRange(0.01, 100_000)
        self.spin_price.setDecimals(2)
        self.spin_price.setSuffix(" TL")
        self.spin_price.setMinimumWidth(180)
        self.spin_price.setMinimumHeight(45)
        self.spin_price.valueChanged.connect(self._update_amount)
        price_row.addWidget(self.spin_price)

        btn_lookup = QPushButton(L10N.FIYAT_AL)
        btn_lookup.setCursor(Qt.PointingHandCursor)
        btn_lookup.setProperty("cssClass", "primaryButton")
        btn_lookup.setMinimumHeight(45)
        btn_lookup.clicked.connect(self._on_lookup)
        price_row.addWidget(btn_lookup)
        form.addRow(L10N.FIYAT_1, price_row)

        self.edit_amount = QLineEdit()
        self.edit_amount.setReadOnly(True)
        self.edit_amount.setMinimumHeight(45)
        self.edit_amount.setProperty("cssClass", "tradeInputNormal")
        form.addRow(L10N.TUTAR_1, self.edit_amount)
        self.spin_qty.valueChanged.connect(self._update_amount)
        self._update_amount()

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setMinimumHeight(45)
        form.addRow(L10N.TARIH_1, self.date_edit)

        self.time_edit = QTimeEdit(QTime.currentTime())
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setMinimumHeight(45)
        form.addRow("Saat:", self.time_edit)

        layout.addLayout(form)
        layout.addStretch()

        button_row = QHBoxLayout()
        button_row.addStretch()
        btn_cancel = QPushButton(L10N.CANCEL)
        btn_cancel.setMinimumHeight(40)
        btn_cancel.setProperty("cssClass", "secondaryButton")
        btn_cancel.clicked.connect(self.reject)

        self.btn_action = QPushButton(L10N.AL if self.side == "BUY" else L10N.SAT)
        self.btn_action.setMinimumHeight(40)
        self.btn_action.setProperty("cssClass", "successButton" if self.side == "BUY" else "dangerButton")
        self.btn_action.clicked.connect(self.accept)
        self.btn_action.setDefault(True)

        button_row.addWidget(btn_cancel)
        button_row.addWidget(self.btn_action)
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
            logger.warning("Fiyat sorgulama başarısız (%s): %s", ticker, exc)

    def _update_amount(self):
        amount = Decimal(self.spin_qty.value()) * self.spin_price.decimal_value()
        self.edit_amount.setText(f"{amount:,.2f} TL")

    def _on_enter_pressed(self):
        if self.focusWidget() is self.txt_ticker and self.price_lookup_func and self.spin_price.value() <= 0.01:
            self._on_lookup()
            return
        self.accept()

    def get_result(self) -> Optional[dict]:
        ticker = self.txt_ticker.text().strip()
        if not ticker:
            return None
        return {
            "ticker": ticker.upper(),
            "quantity": self.spin_qty.value(),
            "price": self.spin_price.decimal_value(),
            "trade_date": self.date_edit.date().toPyDate(),
            "trade_time": self.time_edit.time().toPyTime(),
        }

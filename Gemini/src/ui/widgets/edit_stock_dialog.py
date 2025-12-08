# src/ui/widgets/edit_stock_dialog.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)

from src.domain.models.stock import Stock


@dataclass
class EditStockResult:
    ticker: str
    name: Optional[str]


class EditStockDialog(QDialog):
    """
    Seçili hissenin ticker ve adını düzenlemek için kullanılan dialog.
    İşlem/trade değiştirmez, sadece stocks tablosunu günceller.
    """

    def __init__(self, stock: Stock, parent=None):
        super().__init__(parent)
        self._stock = stock
        self._init_ui()
        self._connect_signals()

        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

    def _init_ui(self):
        self.setWindowTitle("Hisseyi Düzenle")
        self.setMinimumWidth(420)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        title = QLabel("Hisse bilgilerini düzenleyebilirsiniz.")
        title.setObjectName("summaryLabel")
        main_layout.addWidget(title)

        sub = QLabel("Ticker değiştirirken BIST için sadece kod yazmanız yeterli (örn: ASELS). "
                     "Sistem otomatik .IS ekleyecek.")
        sub.setWordWrap(True)
        main_layout.addWidget(sub)

        line = QLabel()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #1f2937;")
        main_layout.addWidget(line)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)

        self.edit_ticker = QLineEdit(self._stock.ticker)
        self.edit_name = QLineEdit(self._stock.name or "")

        form.addRow("Ticker:", self.edit_ticker)
        form.addRow("Hisse Adı:", self.edit_name)

        main_layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_ok = QPushButton("Kaydet")
        self.btn_ok.setObjectName("primaryButton")
        self.btn_cancel = QPushButton("İptal")

        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(btn_layout)

    def _connect_signals(self):
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

    def get_result(self) -> Optional[EditStockResult]:
        if self.result() != QDialog.Accepted:
            return None

        ticker = self.edit_ticker.text().strip().upper()
        name = self.edit_name.text().strip() or None

        if not ticker:
            raise ValueError("Ticker boş olamaz.")

        # BIST için .IS ekle (eğer yoksa)
        if "." not in ticker:
            ticker = ticker + ".IS"

        return EditStockResult(ticker=ticker, name=name)

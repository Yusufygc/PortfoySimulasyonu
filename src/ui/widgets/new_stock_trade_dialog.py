# src/ui/widgets/new_stock_trade_dialog.py

from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Optional, Literal, Dict, Any

from PyQt5.QtCore import Qt, QDate, QTime
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QSpinBox,
    
    QDateEdit,
    QTimeEdit,
    QPushButton,
    QMessageBox,
)

SideLiteral = Literal["BUY", "SELL"]


class NewStockTradeDialog(QDialog):
    """
    İlk defa hisse eklerken ya da yeni bir hissede işlem açarken kullanılan dialog.

    Hem:
      - ticker / hisse adı (stock)
      - trade bilgisi (BUY/SELL, lot, fiyat, tarih)
    toplar.

    Dışarıya basit bir dict döner.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        self.setWindowTitle("Yeni Hisse / İşlem Ekle")
        self.setModal(True)
        self.resize(420, 280)

        main_layout = QVBoxLayout(self)

        # Başlık
        header = QLabel("Yeni hisse ekleyip ilk işlemini girebilirsiniz.")
        header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        main_layout.addWidget(header)

        form_layout = QFormLayout()

        # Ticker
        self.line_ticker = QLineEdit()
        self.line_ticker.setPlaceholderText("Örn: AKBNK.IS")
        form_layout.addRow("Ticker:", self.line_ticker)

        # Hisse adı (opsiyonel)
        self.line_name = QLineEdit()
        self.line_name.setPlaceholderText("Örn: Akbank T.A.Ş. (isteğe bağlı)")
        form_layout.addRow("Hisse Adı:", self.line_name)

        # Tarih / saat
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime.currentTime())

        form_layout.addRow("Tarih:", self.date_edit)
        form_layout.addRow("Saat:", self.time_edit)

        # BUY / SELL
        side_layout = QHBoxLayout()
        self.radio_buy = QRadioButton("Alış (BUY)")
        self.radio_sell = QRadioButton("Satış (SELL)")
        self.radio_buy.setChecked(True)
        side_layout.addWidget(self.radio_buy)
        side_layout.addWidget(self.radio_sell)
        side_layout.addStretch()
        form_layout.addRow("İşlem Türü:", side_layout)

        # Lot
        self.spin_quantity = QSpinBox()
        self.spin_quantity.setMinimum(1)
        self.spin_quantity.setMaximum(10_000_000)
        self.spin_quantity.setValue(1)
        form_layout.addRow("Lot:", self.spin_quantity)

        # Fiyat (artık QLineEdit, virgülü kendimiz parse edeceğiz)
        self.edit_price = QLineEdit()
        self.edit_price.setPlaceholderText("Örn: 9,18 veya 9.18")
        form_layout.addRow("Fiyat:", self.edit_price)


        main_layout.addLayout(form_layout)

        # Butonlar
        buttons_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Kaydet")
        self.btn_cancel = QPushButton("İptal")
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_ok)
        buttons_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(buttons_layout)

    def _connect_signals(self):
        self.btn_ok.clicked.connect(self._on_ok_clicked)
        self.btn_cancel.clicked.connect(self.reject)

    def _on_ok_clicked(self):
        try:
            _ = self._collect_data()
        except ValueError as e:
            QMessageBox.warning(self, "Geçersiz Girdi", str(e))
            return
        self.accept()

    def _collect_data(self) -> Dict[str, Any]:
        ticker = self.line_ticker.text().strip().upper()
        if not ticker:
            raise ValueError("Lütfen ticker girin (örn: AKBNK veya AKBNK.IS).")

        # BIST kısaltması girilirse otomatik .IS ekleyelim
        # Örn: ASELS → ASELS.IS
        if "." not in ticker:
            ticker = ticker + ".IS"


        name = self.line_name.text().strip() or None

        qdate: QDate = self.date_edit.date()
        qtime: QTime = self.time_edit.time()
        trade_date = date(qdate.year(), qdate.month(), qdate.day())
        trade_time = time(qtime.hour(), qtime.minute())

        if self.radio_buy.isChecked():
            side: SideLiteral = "BUY"
        elif self.radio_sell.isChecked():
            side = "SELL"
        else:
            raise ValueError("Lütfen işlem türünü seçin (Alış/Satış).")

        quantity = self.spin_quantity.value()
        if quantity <= 0:
            raise ValueError("Lot sayısı pozitif olmalıdır.")

        raw_text = self.edit_price.text().strip()
        if not raw_text:
            raise ValueError("Lütfen fiyat girin.")

        raw_text = raw_text.replace(",", ".")  # 9,18 -> 9.18

        try:
            price = Decimal(raw_text)
        except Exception:
            raise ValueError("Geçerli bir fiyat girin. Örn: 9,18")

        if price <= 0:
            raise ValueError("Fiyat pozitif olmalıdır.")

        print("DEBUG NewStockTradeDialog price text:", repr(raw_text), "Decimal:", price)



        return {
            "ticker": ticker,
            "name": name,
            "trade_date": trade_date,
            "trade_time": trade_time,
            "side": side,
            "quantity": quantity,
            "price": price,
        }

    def get_result(self) -> Optional[Dict[str, Any]]:
        """
        Dialog ACCEPT ile kapandıysa dict döner, aksi halde None.
        """
        if self.result() != QDialog.Accepted:
            return None
        return self._collect_data()

# src/ui/widgets/trade_dialog.py

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional, Literal

from PyQt5.QtCore import Qt, QDate, QTime
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QRadioButton,
    QSpinBox,
    QLineEdit,
    QDateEdit,
    QTimeEdit,
    QPushButton,
    QMessageBox,
)

# İstersen direkt Trade domain modelini burada kullanmayıp
# sadece dict döndürebilirsin. Şimdilik dict döndürelim.
SideLiteral = Literal["BUY", "SELL"]


class TradeDialog(QDialog):
    """
    Hisseye çift tıklayınca açılan alış/satış işlemi dialog'u.

    Bu dialog DB'ye yazmaz, domain'i bilmez;
    sadece kullanıcıdan veri toplar ve "trade_data" döner.

    MainWindow:
      - dialog.exec_()
      - dialog.get_trade_data() → dict
      - PortfolioService.add_trade(...) çağırır.
    """

    def __init__(
        self,
        stock_id: int,
        ticker: Optional[str] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.stock_id = stock_id
        self.ticker = ticker

        self._init_ui()
        self._connect_signals()

    # --------- UI kurulum --------- #

    def _init_ui(self):
        self.setWindowTitle("Yeni İşlem (Alış / Satış)")
        self.setModal(True)
        self.resize(400, 250)

        main_layout = QVBoxLayout(self)

        # Üstte hisse bilgisi
        header_layout = QHBoxLayout()
        lbl_title = QLabel("Hisse:")
        if self.ticker:
            self.lbl_stock = QLabel(f"{self.ticker} (ID: {self.stock_id})")
        else:
            self.lbl_stock = QLabel(f"ID: {self.stock_id}")
        header_layout.addWidget(lbl_title)
        header_layout.addWidget(self.lbl_stock)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # Form alanları
        form_layout = QFormLayout()

        # Tarih
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())

        # Saat (opsiyonel)
        self.time_edit = QTimeEdit()
        self.time_edit.setTime(QTime.currentTime())
        self.time_edit.setDisplayFormat("HH:mm")

        # Alış / Satış
        side_layout = QHBoxLayout()
        self.radio_buy = QRadioButton("Alış (BUY)")
        self.radio_sell = QRadioButton("Satış (SELL)")
        self.radio_buy.setChecked(True)
        side_layout.addWidget(self.radio_buy)
        side_layout.addWidget(self.radio_sell)
        side_layout.addStretch()

        # Lot sayısı
        self.spin_quantity = QSpinBox()
        self.spin_quantity.setMinimum(1)
        self.spin_quantity.setMaximum(10_000_000)
        self.spin_quantity.setValue(1)

        # Fiyat (QLineEdit)
        self.edit_price = QLineEdit()
        self.edit_price.setPlaceholderText("Örn: 9,18 veya 9.18")
        form_layout.addRow("Fiyat:", self.edit_price)


        form_layout.addRow("Tarih:", self.date_edit)
        form_layout.addRow("Saat:", self.time_edit)
        form_layout.addRow("İşlem Türü:", side_layout)
        form_layout.addRow("Lot:", self.spin_quantity)
        form_layout.addRow("Fiyat:", self.edit_price)

        main_layout.addLayout(form_layout)

        # Alt kısım: butonlar
        button_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Kaydet")
        self.btn_cancel = QPushButton("İptal")
        button_layout.addStretch()
        button_layout.addWidget(self.btn_ok)
        button_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(button_layout)

    def _connect_signals(self):
        self.btn_ok.clicked.connect(self._on_ok_clicked)
        self.btn_cancel.clicked.connect(self.reject)

    # --------- OK tıklanınca doğrulama --------- #

    def _on_ok_clicked(self):
        try:
            # Bir defa parse edip hata varsa exception ile yakalayalım
            _ = self._build_trade_data()
        except ValueError as e:
            QMessageBox.warning(self, "Geçersiz Girdi", str(e))
            return

        self.accept()

    # --------- Dışarıya verilecek trade_data --------- #

    def _build_trade_data(self) -> dict:
        qdate: QDate = self.date_edit.date()
        qtime: QTime = self.time_edit.time()

        trade_date = date(qdate.year(), qdate.month(), qdate.day())
        trade_time = time(qtime.hour(), qtime.minute())

        if self.radio_buy.isChecked():
            side: SideLiteral = "BUY"
        elif self.radio_sell.isChecked():
            side = "SELL"
        else:
            raise ValueError("Lütfen işlem türünü seçin (Alış veya Satış).")

        quantity = self.spin_quantity.value()
        if quantity <= 0:
            raise ValueError("Lot sayısı pozitif olmalıdır.")

        raw_text = self.edit_price.text().strip()
        if not raw_text:
            raise ValueError("Lütfen fiyat girin.")

        raw_text = raw_text.replace(",", ".")  # 1,25 -> 1.25

        try:
            price = Decimal(raw_text)
        except Exception:
            raise ValueError("Geçerli bir fiyat girin. Örn: 1,25")

        if price <= 0:
            raise ValueError("Fiyat pozitif olmalıdır.")

        print("DEBUG TradeDialog price text:", repr(raw_text), "Decimal:", price)


        return {
            "stock_id": self.stock_id,
            "trade_date": trade_date,
            "trade_time": trade_time,
            "side": side,
            "quantity": quantity,
            "price": price,
        }


    def get_trade_data(self) -> Optional[dict]:
        """
        Dialog ACCEPT ile kapandıysa trade_data döner,
        İPTAL ise None döner.
        """
        if self.result() != QDialog.Accepted:
            return None
        return self._build_trade_data()

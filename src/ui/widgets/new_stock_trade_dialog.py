# src/ui/widgets/new_stock_trade_dialog.py

from __future__ import annotations

from datetime import date, time,dt_date
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

        # Yardım butonunu ( ? ) kapat
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        # Başlangıçta ticker alanına odaklan
        self.line_ticker.setFocus()

        # Parent ortasına taşı
        if parent is not None:
            geo = parent.geometry()
            self.move(
                geo.center().x() - self.width() // 2,
                geo.center().y() - self.height() // 2,
            )

    def _init_ui(self):
        self.setWindowTitle("Yeni Hisse / İşlem Ekle")
        self.setModal(True)
        self.setMinimumWidth(520)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # ----- Header -----
        title = QLabel("Yeni hisse ekleyip ilk işlemini girebilirsiniz.")
        title.setObjectName("summaryLabel")  # style.py'deki daha güçlü fontu kullanalım
        title.setWordWrap(True)

        subtitle = QLabel(
            "BIST hisseleri için sadece kod yazmanız yeterli (örn: AKBNK). "
            "Sistem otomatik olarak .IS ekleyecek."
        )
        subtitle.setWordWrap(True)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # Küçük bir ayraç
        line = QLabel()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #1f2937;")
        main_layout.addWidget(line)

        # ----- Form -----
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form_layout.setFormAlignment(Qt.AlignTop)
        form_layout.setHorizontalSpacing(16)
        form_layout.setVerticalSpacing(10)

        # Ticker
        self.line_ticker = QLineEdit()
        self.line_ticker.setPlaceholderText("Örn: AKBNK")
        form_layout.addRow("Ticker:", self.line_ticker)

        # Hisse adı
        self.line_name = QLineEdit()
        self.line_name.setPlaceholderText("Örn: Akbank T.A.Ş. (isteğe bağlı)")
        form_layout.addRow("Hisse Adı:", self.line_name)

        # Tarih
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form_layout.addRow("Tarih:", self.date_edit)

        # Saat
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime.currentTime())
        form_layout.addRow("Saat:", self.time_edit)

        # İşlem türü
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
        self.spin_quantity.setValue(100)
        form_layout.addRow("Lot:", self.spin_quantity)

        # Fiyat
        self.edit_price = QLineEdit()
        self.edit_price.setPlaceholderText("Örn: 9,18 veya 9.18")
        form_layout.addRow("Fiyat:", self.edit_price)

        main_layout.addLayout(form_layout)

        # ----- Alt aksiyon butonları -----
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.btn_ok = QPushButton("Kaydet")
        self.btn_cancel = QPushButton("İptal")

        # Kaydet butonunu primary gibi göstermek için id ver
        self.btn_ok.setObjectName("primaryButton")

        button_layout.addWidget(self.btn_ok)
        button_layout.addWidget(self.btn_cancel)

        main_layout.addSpacing(6)
        main_layout.addLayout(button_layout)


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

        today_py = dt_date.today()
        if trade_date > today_py:
            raise ValueError("Gelecek tarih için işlem girilemez.")

        if trade_date.weekday() >= 5:
            raise ValueError("Hafta sonu tarihine işlem girilemez (Cumartesi/Pazar).")

        if not (10 <= trade_time.hour < 18):
            raise ValueError("İşlem saati 10:00 ile 18:00 arasında olmalıdır.")

                # --- Tarih / saat validasyonu ---
        # Hafta sonu (Cumartesi = 5, Pazar = 6) engelle
        if trade_date.weekday() >= 5:
            raise ValueError("Hafta sonu tarihine işlem ekleyemezsiniz (Cumartesi/Pazar).")

        # Saat 10:00 - 18:00 aralığında olmalı
        if not (10 <= trade_time.hour < 18):
            raise ValueError("İşlem saati 10:00 ile 18:00 arasında olmalıdır.")


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

    def _normalize_trade_date(self, qdate: QDate) -> QDate:
        """Hafta sonu / geleceğe taşan tarihleri düzeltir."""
        today_q = QDate.currentDate()

        # Gelecek tarihse bugüne çek
        if qdate > today_q:
            return today_q

        # Qt: 1=PAZARTESİ ... 6=CUMARTESİ, 7=PAZAR
        weekday = qdate.dayOfWeek()
        if weekday == 6:      # Cumartesi
            return qdate.addDays(-1)
        elif weekday == 7:    # Pazar
            return qdate.addDays(-2)
        return qdate

    def _on_date_changed(self, new_date: QDate):
        fixed = self._normalize_trade_date(new_date)
        if fixed != new_date:
            # Sonsuz döngüye girmemek için sinyali blokla
            self.date_edit.blockSignals(True)
            self.date_edit.setDate(fixed)
            self.date_edit.blockSignals(False)
            # İstersen sessiz de yapabilirsin; bilgi mesajı opsiyonel:
            # QMessageBox.information(
            #     self, "Tarih Düzenlendi",
            #     "Hafta sonu / gelecekteki tarihler için işlem girilemez.\n"
            #     "Tarih en yakın iş gününe çekildi."
            # )

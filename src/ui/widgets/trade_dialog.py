# src/ui/widgets/trade_dialog.py

from __future__ import annotations

from datetime import date, datetime, time
from datetime import date as dt_date 
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
DialogMode = Literal["trade", "edit_stock"]

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
        self._mode: DialogMode = "trade"   # <-- eklendi
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
        today_q = QDate.currentDate()
        normalized_today = self._normalize_trade_date(today_q)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(normalized_today)
        self.date_edit.setMaximumDate(today_q)


        # Sinyal bağla: kullanıcı tarihi değiştirince hafta sonuna izin vermeyelim
        self.date_edit.dateChanged.connect(self._on_date_changed)

        # Saat (opsiyonel)
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")

        min_t = QTime(10, 0)
        max_t = QTime(17, 59)  # 18:00 hariç

        # Varsayılan: şu an bu aralıktaysa onu, değilse 10:00
        now_t = QTime.currentTime()
        if now_t < min_t or now_t > max_t:
            self.time_edit.setTime(min_t)
        else:
            self.time_edit.setTime(now_t)

        self.time_edit.setMinimumTime(min_t)
        self.time_edit.setMaximumTime(max_t)

        # Kullanıcı manuel yazarsa da clamp’leyelim
        self.time_edit.timeChanged.connect(self._on_time_changed)


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
        button_layout.addStretch()

        self.btn_edit_stock = QPushButton("Hisseyi Düzenle")
        self.btn_ok = QPushButton("İşlem Kaydet")
        self.btn_cancel = QPushButton("İptal")

        self.btn_ok.setObjectName("primaryButton")

        button_layout.addWidget(self.btn_edit_stock)
        button_layout.addWidget(self.btn_ok)
        button_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(button_layout)


    def _connect_signals(self):
        self.btn_ok.clicked.connect(self._on_ok_clicked)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_edit_stock.clicked.connect(self._on_edit_stock_clicked)

    # --------- Hisse düzenleme butonu --------- #
    def _on_edit_stock_clicked(self):
        """
        Hisseyi düzenle moduna geçer; trade kaydetmez.
        """
        self._mode = "edit_stock"
        self.accept()


    # --------- OK tıklanınca doğrulama --------- #

    def _on_ok_clicked(self):
        try:
            _ = self._build_trade_data()
        except ValueError as e:
            QMessageBox.warning(self, "Geçersiz Girdi", str(e))
            return

        self._mode = "trade"
        self.accept()


    # --------- Dışarıya verilecek trade_data --------- #

    def _build_trade_data(self) -> dict:
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
        if trade_date.weekday() >= 5:
            raise ValueError("Hafta sonu tarihine işlem ekleyemezsiniz (Cumartesi/Pazar).")

        if not (10 <= trade_time.hour < 18):
            raise ValueError("İşlem saati 10:00 ile 18:00 arasında olmalıdır.")


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


    def get_mode(self) -> DialogMode:
        return self._mode

    def get_trade_data(self) -> Optional[dict]:
        """
        Sadece 'trade' modunda ACCEPT ile kapandıysa trade_data döner.
        """
        if self.result() != QDialog.Accepted:
            return None
        if self._mode != "trade":
            return None
        return self._build_trade_data()

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
    
    def _on_time_changed(self, new_time: QTime):
        min_t = QTime(10, 0)
        max_t = QTime(17, 59)

        fixed = new_time
        if new_time < min_t:
            fixed = min_t
        elif new_time > max_t:
            fixed = max_t

        if fixed != new_time:
            self.time_edit.blockSignals(True)
            self.time_edit.setTime(fixed)
            self.time_edit.blockSignals(False)

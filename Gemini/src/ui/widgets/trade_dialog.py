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
        price_lookup_func=None,
        lot_size: int = 1,
    ):
        super().__init__(parent)
        self.stock_id = stock_id
        self.ticker = ticker

        # yeni alanlar
        self.price_lookup_func = price_lookup_func
        self.lot_size = lot_size
        self.current_price: Optional[Decimal] = None
        self._updating_amount = False
        self._updating_quantity = False

        self._init_ui()
        self._connect_signals()
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        # ticker varsa açılışta fiyatı çek
        if self.ticker and self.price_lookup_func:
            self._fetch_initial_price()

       # --------- UI kurulum --------- #

    def _init_ui(self):
        self.setWindowTitle("Yeni İşlem (Alış / Satış)")
        self.setModal(True)
        self.setMinimumWidth(520)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # ---------- HEADER ----------
        header_layout = QVBoxLayout()

        if self.ticker:
            title_text = f"Hisse: {self.ticker} (ID: {self.stock_id})"
        else:
            title_text = f"Hisse ID: {self.stock_id}"

        self.lbl_header = QLabel(title_text)
        self.lbl_header.setObjectName("summaryLabel")

        # Güncel fiyat label'ı (yfinance)
        self.lbl_market_price = QLabel("Güncel Fiyat (yfinance): -")

        header_layout.addWidget(self.lbl_header)
        header_layout.addWidget(self.lbl_market_price)

        main_layout.addLayout(header_layout)

        # ---------- FORM ----------
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form_layout.setHorizontalSpacing(16)
        form_layout.setVerticalSpacing(10)

        # LOT
        self.spin_quantity = QSpinBox()
        self.spin_quantity.setMinimum(1)
        self.spin_quantity.setMaximum(10_000_000)
        self.spin_quantity.setValue(100)
        form_layout.addRow("Lot:", self.spin_quantity)

        # TUTAR (TL)
        self.edit_amount = QLineEdit()
        self.edit_amount.setPlaceholderText("Örn: 15000 (TL)")
        form_layout.addRow("Tutar (TL):", self.edit_amount)

        # FİYAT
        self.edit_price = QLineEdit()
        self.edit_price.setPlaceholderText("Örn: 9,18 veya 9.18")
        form_layout.addRow("Fiyat:", self.edit_price)

        # TARİH
        today_q = QDate.currentDate()
        normalized_today = self._normalize_trade_date(today_q)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(normalized_today)
        self.date_edit.setMaximumDate(today_q)
        form_layout.addRow("Tarih:", self.date_edit)

        # SAAT
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")

        min_t = QTime(10, 0)
        max_t = QTime(17, 59)
        now_t = QTime.currentTime()
        if now_t < min_t or now_t > max_t:
            self.time_edit.setTime(min_t)
        else:
            self.time_edit.setTime(now_t)
        self.time_edit.setMinimumTime(min_t)
        self.time_edit.setMaximumTime(max_t)
        form_layout.addRow("Saat:", self.time_edit)

        # İŞLEM TÜRÜ
        side_layout = QHBoxLayout()
        self.radio_buy = QRadioButton("Alış (BUY)")
        self.radio_sell = QRadioButton("Satış (SELL)")
        self.radio_buy.setChecked(True)
        side_layout.addWidget(self.radio_buy)
        side_layout.addWidget(self.radio_sell)
        side_layout.addStretch()
        form_layout.addRow("İşlem Türü:", side_layout)

        main_layout.addLayout(form_layout)

        # ---------- ALT BUTONLAR ----------
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

        # Tarih / saat clamp
        self.date_edit.dateChanged.connect(self._on_date_changed)
        self.time_edit.timeChanged.connect(self._on_time_changed)

        # Dinamik para ↔ lot hesaplama
        self.spin_quantity.valueChanged.connect(self._on_quantity_changed)
        self.edit_amount.textChanged.connect(self._on_amount_changed)

    def _fetch_initial_price(self):
        """
        MainWindow'dan gelen price_lookup_func ile:
        - önce intraday,
        - yoksa son kapanış fiyatını çeker.
        Label'ı da buna göre doldurur.
        """
        if not self.price_lookup_func or not self.ticker:
            return

        result = self.price_lookup_func(self.ticker)
        if result is None:
            self.current_price = None
            self.lbl_market_price.setText("Güncel Fiyat (yfinance): Fiyat bulunamadı")
            return

        price = result.price
        self.current_price = price

        if result.source == "intraday":
            info_text = f"{price:.2f} (anlık)"
        else:
            d_str = result.as_of.strftime("%d.%m.%Y")
            info_text = f"{price:.2f} (son kapanış {d_str})"

        self.lbl_market_price.setText(f"Güncel Fiyat (yfinance): {info_text}")

        # Fiyat alanı boşsa otomatik doldur
        if not self.edit_price.text().strip():
            self.edit_price.setText(str(price))

    def _on_quantity_changed(self, value: int):
        if self._updating_amount:
            return
        if self.current_price is None:
            return

        self._updating_quantity = True
        try:
            lot_size = self.lot_size or 1
            total = value * float(self.current_price) * lot_size
            self.edit_amount.setText(f"{total:.2f}")
        finally:
            self._updating_quantity = False

    def _on_amount_changed(self, text: str):
        if self._updating_quantity:
            return
        if self.current_price is None:
            return

        txt = text.strip().replace(",", ".")
        if not txt:
            return

        try:
            amount = float(txt)
        except ValueError:
            return

        if amount <= 0:
            return

        lot_size = self.lot_size or 1
        # alınabilecek maksimum lot sayısı
        max_lot = int(amount // (float(self.current_price) * lot_size))
        if max_lot <= 0:
            return

        self._updating_amount = True
        try:
            self.spin_quantity.setValue(max_lot)
        finally:
            self._updating_amount = False

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

        today_py = date.today()
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

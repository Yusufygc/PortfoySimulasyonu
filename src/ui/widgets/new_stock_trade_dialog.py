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
    def __init__(self, parent=None, price_lookup_func=None, lot_size: int = 1):
        super().__init__(parent)
        self.price_lookup_func = price_lookup_func  # callback
        self.lot_size = lot_size                   # 1 ya da 100 gibi
        self.current_price: Optional[Decimal] = None
        self._updating_amount = False
        self._updating_quantity = False

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
        title.setObjectName("summaryLabel")  # style.py'deki daha güçlü font
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
        today_q = QDate.currentDate()
        normalized_today = self._normalize_trade_date(today_q)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(normalized_today)
        self.date_edit.setMaximumDate(today_q)  # ileri tarih yok

        form_layout.addRow("Tarih:", self.date_edit)

        # Saat
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")

        min_t = QTime(10, 0)
        max_t = QTime(17, 59)  # 18:00 hariç

        now_t = QTime.currentTime()
        if now_t < min_t or now_t > max_t:
            self.time_edit.setTime(min_t)
        else:
            self.time_edit.setTime(now_t)

        self.time_edit.setMinimumTime(min_t)
        self.time_edit.setMaximumTime(max_t)

        form_layout.addRow("Saat:", self.time_edit)

        # --- Piyasa fiyatı gösterimi ---
        self.lbl_market_price = QLabel("-")
        form_layout.addRow("Güncel Fiyat (yfinance):", self.lbl_market_price)

        # Lot
        self.spin_quantity = QSpinBox()
        self.spin_quantity.setMinimum(1)
        self.spin_quantity.setMaximum(10_000_000)
        self.spin_quantity.setValue(100)
        form_layout.addRow("Lot:", self.spin_quantity)

        # Tutar (TL)
        self.edit_amount = QLineEdit()
        self.edit_amount.setPlaceholderText("Örn: 15000 (TL)")
        form_layout.addRow("Tutar (TL):", self.edit_amount)

        # Fiyat
        self.edit_price = QLineEdit()
        self.edit_price.setPlaceholderText("Örn: 9,18 veya 9.18")
        form_layout.addRow("Fiyat:", self.edit_price)

        # ---- İŞLEM TÜRÜ (EN ALTA) ----
        side_layout = QHBoxLayout()
        self.radio_buy = QRadioButton("Alış (BUY)")
        self.radio_sell = QRadioButton("Satış (SELL)")
        self.radio_buy.setChecked(True)

        # Renkler
        self.radio_buy.setStyleSheet("color: #22c55e; font-weight: 600;")
        self.radio_sell.setStyleSheet("color: #ef4444; font-weight: 600;")

        side_layout.addStretch()
        side_layout.addWidget(self.radio_buy)
        side_layout.addWidget(self.radio_sell)
        side_layout.addStretch()
        form_layout.addRow("İşlem Türü:", side_layout)

        main_layout.addLayout(form_layout)

        # ----- Alt aksiyon butonları -----
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.btn_ok = QPushButton("Kaydet")
        self.btn_cancel = QPushButton("İptal")

        self.btn_ok.setObjectName("primaryButton")

        button_layout.addWidget(self.btn_ok)
        button_layout.addWidget(self.btn_cancel)

        main_layout.addSpacing(6)
        main_layout.addLayout(button_layout)

    def _connect_signals(self):
        self.btn_ok.clicked.connect(self._on_ok_clicked)
        self.btn_cancel.clicked.connect(self.reject)

        self.date_edit.dateChanged.connect(self._on_date_changed)
        self.time_edit.timeChanged.connect(self._on_time_changed)

        # Ticker alanı değişince fiyatı getir
        self.line_ticker.editingFinished.connect(self._on_ticker_edited)

        # Dinamik hesaplama
        self.spin_quantity.valueChanged.connect(self._on_quantity_changed)
        self.edit_amount.textChanged.connect(self._on_amount_changed)

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

        today_py = date.today()
        if trade_date > today_py:
            raise ValueError("Gelecek tarih için işlem girilemez.")

        if trade_date.weekday() >= 5:
            raise ValueError("Hafta sonu tarihine işlem girilemez (Cumartesi/Pazar).")

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

    def _on_ticker_edited(self):
        ticker = self.line_ticker.text().strip().upper()
        if not ticker or self.price_lookup_func is None:
            return

        result = self.price_lookup_func(ticker)
        if result is None:
            self.current_price = None
            self.lbl_market_price.setText("Fiyat bulunamadı")
            return

        price = result.price
        self.current_price = price

        # Label metni: fiyat + kaynağı + tarih
        if result.source == "intraday":
            info_text = f"{price:.2f} (anlık)"
        else:
            d_str = result.as_of.strftime("%d.%m.%Y")
            info_text = f"{price:.2f} (son kapanış {d_str})"

        self.lbl_market_price.setText(info_text)

        # Kullanıcı fiyat alanını boş bıraktıysa otomatik dolduralım
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
        text = text.strip().replace(",", ".")
        if not text:
            return
        try:
            amount = float(text)
        except ValueError:
            return

        if amount <= 0:
            return

        lot_size = self.lot_size or 1
        max_lot = int(amount // (float(self.current_price) * lot_size))
        if max_lot <= 0:
            return

        self._updating_amount = True
        try:
            self.spin_quantity.setValue(max_lot)
        finally:
            self._updating_amount = False

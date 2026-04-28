# src/ui/widgets/stock/dialogs/trade_dialog.py

from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Optional, Literal

from PyQt5.QtCore import Qt, QDate, QTime, QThreadPool
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLabel, QRadioButton, QSpinBox, QLineEdit, 
    QDateEdit, QTimeEdit, QPushButton, QMessageBox, QFrame, QWidget
)
from src.ui.worker import Worker

# Tür tanımları
SideLiteral = Literal["BUY", "SELL"]
DialogMode = Literal["trade", "edit_stock"]

class TradeDialog(QDialog):
    """
    Mevcut hisseye işlem ekleme penceresi.
    Tabloya çift tıklayınca açılır.
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
        self.price_lookup_func = price_lookup_func
        self.lot_size = lot_size
        
        self.current_price: Optional[Decimal] = None
        self._mode: DialogMode = "trade"
        
        # State
        self._updating_amount = False
        self._updating_quantity = False

        self._init_ui()
        self._connect_signals()
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        
        # Fiyatı çek
        if self.ticker and self.price_lookup_func:
            self._fetch_initial_price()

    def _init_ui(self):
        self.setWindowTitle("İşlem Ekle")
        self.setMinimumWidth(450)
        # Koyu Tema Arka Planı
        self.setProperty("cssClass", "dialogContainer")

        # Ana Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- HEADER (Üst Bilgi) ---
        header = QFrame()
        header.setProperty("cssClass", "dialogHeaderFrame")
        header.setFixedHeight(75)
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(20, 10, 20, 10)
        h_layout.setSpacing(5)
        
        self.lbl_ticker = QLabel(f"{self.ticker}" if self.ticker else f"ID: {self.stock_id}")
        self.lbl_ticker.setProperty("cssClass", "dialogHeaderTitleLarge")
        
        self.lbl_price_info = QLabel("Fiyat Yükleniyor...")
        self.lbl_price_info.setProperty("cssClass", "dialogSubtitle")
        
        h_layout.addWidget(self.lbl_ticker)
        h_layout.addWidget(self.lbl_price_info)
        
        layout.addWidget(header)

        # --- FORM ALANI ---
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setContentsMargins(30, 30, 30, 30)
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)



        # 1. İşlem Yönü
        side_container = QWidget()
        side_layout = QHBoxLayout(side_container)
        side_layout.setContentsMargins(0, 0, 0, 0)
        
        self.radio_buy = QRadioButton("ALIŞ")
        self.radio_sell = QRadioButton("SATIŞ")
        self.radio_buy.setChecked(True)
        
        self.radio_buy.setProperty("cssClass", "tradeRadioBuy")
        self.radio_sell.setProperty("cssClass", "tradeRadioSell")
        
        side_layout.addWidget(self.radio_buy)
        side_layout.addWidget(self.radio_sell)
        
        lbl_side = QLabel("İşlem:")
        lbl_side.setProperty("cssClass", "formLabel")
        form_layout.addRow(lbl_side, side_container)

        # 2. Tarih / Saat
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setProperty("cssClass", "tradeInputNormal")
        self.time_edit = QTimeEdit(QTime.currentTime())
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setProperty("cssClass", "tradeInputNormal")
        
        # Tarih normalizasyonu
        self._normalize_trade_date(QDate.currentDate())
        
        # Yan yana koyalım
        dt_container = QWidget()
        dt_layout = QHBoxLayout(dt_container)
        dt_layout.setContentsMargins(0, 0, 0, 0)
        dt_layout.setSpacing(10)
        dt_layout.addWidget(self.date_edit)
        dt_layout.addWidget(self.time_edit)
        
        lbl_date = QLabel("Zaman:")
        lbl_date.setProperty("cssClass", "formLabel")
        form_layout.addRow(lbl_date, dt_container)

        # 3. Lot / Fiyat / Tutar
        self.spin_quantity = QSpinBox()
        self.spin_quantity.setRange(1, 10_000_000)
        self.spin_quantity.setValue(1)
        self.spin_quantity.setProperty("cssClass", "tradeInputNormal")
        
        self.edit_price = QLineEdit()
        self.edit_price.setPlaceholderText("0.00")
        self.edit_price.setProperty("cssClass", "tradeInputNormal")
        
        self.edit_amount = QLineEdit()
        self.edit_amount.setPlaceholderText("Toplam Tutar")
        self.edit_amount.setProperty("cssClass", "tradeInputNormal")

        lbl_lot = QLabel("Adet (Lot):")
        lbl_lot.setProperty("cssClass", "formLabel")
        lbl_price = QLabel("Birim Fiyat:")
        lbl_price.setProperty("cssClass", "formLabel")
        lbl_total = QLabel("Toplam:")
        lbl_total.setProperty("cssClass", "formLabel")

        form_layout.addRow(lbl_lot, self.spin_quantity)
        form_layout.addRow(lbl_price, self.edit_price)
        form_layout.addRow(lbl_total, self.edit_amount)

        layout.addWidget(form_widget)
        layout.addStretch()

        # --- FOOTER (Butonlar) ---
        footer = QFrame()
        footer.setProperty("cssClass", "dialogFooterFrame")
        footer.setFixedHeight(70)
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(20, 10, 20, 10)

        self.btn_edit_stock = QPushButton("Hisse Bilgisini Düzenle")
        self.btn_edit_stock.setCursor(Qt.PointingHandCursor)
        self.btn_edit_stock.setProperty("cssClass", "linkButton")

        self.btn_save = QPushButton("Kaydet")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setProperty("cssClass", "primaryButton")

        f_layout.addWidget(self.btn_edit_stock)
        f_layout.addStretch()
        f_layout.addWidget(self.btn_save)

        layout.addWidget(footer)

    def _connect_signals(self):
        self.btn_save.clicked.connect(self._on_ok_clicked)
        self.btn_edit_stock.clicked.connect(self._on_edit_stock_clicked)
        
        # Hesaplamalar
        self.spin_quantity.valueChanged.connect(self._on_quantity_changed)
        self.edit_amount.textChanged.connect(self._on_amount_changed)
        
        # Tarih kontrol
        self.date_edit.dateChanged.connect(self._on_date_changed)
        self.time_edit.timeChanged.connect(self._on_time_changed)

    def _fetch_initial_price(self):
        if not self.price_lookup_func or not self.ticker: return
        
        self.lbl_price_info.setText("⏳ Yükleniyor...")
        self.btn_save.setEnabled(False)

        worker = Worker(self.price_lookup_func, self.ticker)
        worker.signals.result.connect(self._on_price_fetched)
        worker.signals.error.connect(self._on_price_error)
        QThreadPool.globalInstance().start(worker)

    def _on_price_fetched(self, res):
        if res:
            self.current_price = res.price
            self.lbl_price_info.setText(f"Güncel: ₺ {res.price:,.2f} ({'Anlık' if res.source=='intraday' else 'Kapanış'})")
            if not self.edit_price.text():
                self.edit_price.setText(str(res.price))
        else:
            self.lbl_price_info.setText("Fiyat verisi alınamadı.")
        self.btn_save.setEnabled(True)

    def _on_price_error(self, err_tuple):
        self.lbl_price_info.setText("Ağ Hatası")
        self.btn_save.setEnabled(True)

    # --- HESAPLAMA MANTIĞI ---
    def _on_quantity_changed(self, val):
        if self._updating_amount: return
        try:
            p = float(self.edit_price.text().replace(",", ".") or 0)
            self._updating_quantity = True
            self.edit_amount.setText(f"{val * p:.2f}")
            self._updating_quantity = False
        except (ValueError, TypeError): pass

    def _on_amount_changed(self, text):
        if self._updating_quantity: return
        try:
            p = float(self.edit_price.text().replace(",", ".") or 0)
            amt = float(text.replace(",", ".") or 0)
            if p > 0:
                self._updating_amount = True
                self.spin_quantity.setValue(int(amt / p))
                self._updating_amount = False
        except (ValueError, TypeError): pass

    # --- TARİH KONTROLLERİ ---
    def _normalize_trade_date(self, qdate: QDate):
        now = QDate.currentDate()
        if qdate > now: self.date_edit.setDate(now)
        elif qdate.dayOfWeek() > 5: # Haftasonu
            self.date_edit.setDate(qdate.addDays(-(qdate.dayOfWeek() - 5)))

    def _on_date_changed(self, date):
        self._normalize_trade_date(date)

    def _on_time_changed(self, time):
        # 10:00 - 18:00 arası
        if time.hour() < 10: self.time_edit.setTime(QTime(10, 0))
        elif time.hour() >= 18: self.time_edit.setTime(QTime(17, 59))

    # --- BUTON AKSİYONLARI ---
    def _on_edit_stock_clicked(self):
        self._mode = "edit_stock"
        self.accept()

    def _on_ok_clicked(self):
        # Validasyon
        try:
            p = float(self.edit_price.text().replace(",", ".") or 0)
            if p <= 0: raise ValueError("Fiyat 0 olamaz")
        except (ValueError, TypeError):
            QMessageBox.warning(self, "Hata", "Geçersiz fiyat.")
            return
            
        self._mode = "trade"
        self.accept()

    # --- PUBLIC METHODS ---
    def get_mode(self) -> DialogMode:
        return self._mode

    def get_trade_data(self) -> Optional[dict]:
        if self.result() != QDialog.Accepted or self._mode != "trade":
            return None
            
        try:
            price = Decimal(self.edit_price.text().replace(",", "."))
        except (ValueError, Exception): price = Decimal("0")

        return {
            "stock_id": self.stock_id,
            "trade_date": self.date_edit.date().toPyDate(),
            "trade_time": self.time_edit.time().toPyTime(),
            "side": "BUY" if self.radio_buy.isChecked() else "SELL",
            "quantity": self.spin_quantity.value(),
            "price": price
        }

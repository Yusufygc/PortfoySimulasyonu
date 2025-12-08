# src/ui/widgets/trade_dialog.py

from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Optional, Literal

from PyQt5.QtCore import Qt, QDate, QTime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLabel, QRadioButton, QSpinBox, QLineEdit, 
    QDateEdit, QTimeEdit, QPushButton, QMessageBox, QFrame, QWidget
)

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
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        # Ana Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- HEADER (Üst Bilgi) ---
        header = QFrame()
        header.setStyleSheet("background-color: #1e293b; border-bottom: 1px solid #334155;")
        header.setFixedHeight(75)
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(20, 10, 20, 10)
        h_layout.setSpacing(5)
        
        self.lbl_ticker = QLabel(f"{self.ticker}" if self.ticker else f"ID: {self.stock_id}")
        self.lbl_ticker.setStyleSheet("font-size: 18px; font-weight: bold; color: #3b82f6;")
        
        self.lbl_price_info = QLabel("Fiyat Yükleniyor...")
        self.lbl_price_info.setStyleSheet("font-size: 13px; color: #94a3b8;")
        
        h_layout.addWidget(self.lbl_ticker)
        h_layout.addWidget(self.lbl_price_info)
        
        layout.addWidget(header)

        # --- FORM ALANI ---
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setContentsMargins(30, 30, 30, 30)
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Input Stili
        input_style = """
            QLineEdit, QSpinBox, QDateEdit, QTimeEdit {
                background-color: #1e293b; 
                border: 1px solid #334155; 
                border-radius: 6px; 
                padding: 10px;
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus, QSpinBox:focus { border: 1px solid #3b82f6; }
            QDateEdit::drop-down { border: none; }
        """
        self.setStyleSheet(self.styleSheet() + input_style)
        
        label_style = "color: #cbd5e1; font-weight: 500;"

        # 1. İşlem Yönü
        side_container = QWidget()
        side_layout = QHBoxLayout(side_container)
        side_layout.setContentsMargins(0, 0, 0, 0)
        
        self.radio_buy = QRadioButton("ALIŞ")
        self.radio_sell = QRadioButton("SATIŞ")
        self.radio_buy.setChecked(True)
        
        # Radio butonlarını özelleştir
        radio_style = """
            QRadioButton { font-weight: bold; color: white; font-size: 14px; }
            QRadioButton::indicator:checked { border: 2px solid; border-radius: 6px; }
        """
        self.radio_buy.setStyleSheet(radio_style + "QRadioButton::indicator:checked { background-color: #22c55e; border-color: #22c55e; }")
        self.radio_sell.setStyleSheet(radio_style + "QRadioButton::indicator:checked { background-color: #ef4444; border-color: #ef4444; }")
        
        side_layout.addWidget(self.radio_buy)
        side_layout.addWidget(self.radio_sell)
        
        lbl_side = QLabel("İşlem:")
        lbl_side.setStyleSheet(label_style)
        form_layout.addRow(lbl_side, side_container)

        # 2. Tarih / Saat
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.time_edit = QTimeEdit(QTime.currentTime())
        self.time_edit.setDisplayFormat("HH:mm")
        
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
        lbl_date.setStyleSheet(label_style)
        form_layout.addRow(lbl_date, dt_container)

        # 3. Lot / Fiyat / Tutar
        self.spin_quantity = QSpinBox()
        self.spin_quantity.setRange(1, 10_000_000)
        self.spin_quantity.setValue(1)
        
        self.edit_price = QLineEdit()
        self.edit_price.setPlaceholderText("0.00")
        
        self.edit_amount = QLineEdit()
        self.edit_amount.setPlaceholderText("Toplam Tutar")

        lbl_lot = QLabel("Adet (Lot):")
        lbl_lot.setStyleSheet(label_style)
        lbl_price = QLabel("Birim Fiyat:")
        lbl_price.setStyleSheet(label_style)
        lbl_total = QLabel("Toplam:")
        lbl_total.setStyleSheet(label_style)

        form_layout.addRow(lbl_lot, self.spin_quantity)
        form_layout.addRow(lbl_price, self.edit_price)
        form_layout.addRow(lbl_total, self.edit_amount)

        layout.addWidget(form_widget)
        layout.addStretch()

        # --- FOOTER (Butonlar) ---
        footer = QFrame()
        footer.setStyleSheet("background-color: #0f172a; border-top: 1px solid #334155;")
        footer.setFixedHeight(70)
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(20, 10, 20, 10)

        self.btn_edit_stock = QPushButton("Hisse Bilgisini Düzenle")
        self.btn_edit_stock.setCursor(Qt.PointingHandCursor)
        self.btn_edit_stock.setStyleSheet("""
            QPushButton { color: #94a3b8; background: transparent; border: none; font-size: 13px; }
            QPushButton:hover { color: #f8fafc; text-decoration: underline; }
        """)

        self.btn_save = QPushButton("Kaydet")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet("""
            QPushButton { 
                background-color: #3b82f6; color: white; 
                border-radius: 6px; padding: 10px 30px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)

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
        
        res = self.price_lookup_func(self.ticker)
        if res:
            self.current_price = res.price
            self.lbl_price_info.setText(f"Güncel: ₺ {res.price:,.2f} ({'Anlık' if res.source=='intraday' else 'Kapanış'})")
            if not self.edit_price.text():
                self.edit_price.setText(str(res.price))
        else:
            self.lbl_price_info.setText("Fiyat verisi alınamadı.")

    # --- HESAPLAMA MANTIĞI ---
    def _on_quantity_changed(self, val):
        if self._updating_amount: return
        try:
            p = float(self.edit_price.text().replace(",", ".") or 0)
            self._updating_quantity = True
            self.edit_amount.setText(f"{val * p:.2f}")
            self._updating_quantity = False
        except: pass

    def _on_amount_changed(self, text):
        if self._updating_quantity: return
        try:
            p = float(self.edit_price.text().replace(",", ".") or 0)
            amt = float(text.replace(",", ".") or 0)
            if p > 0:
                self._updating_amount = True
                self.spin_quantity.setValue(int(amt / p))
                self._updating_amount = False
        except: pass

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
        except:
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
        except: price = Decimal("0")

        return {
            "stock_id": self.stock_id,
            "trade_date": self.date_edit.date().toPyDate(),
            "trade_time": self.time_edit.time().toPyTime(),
            "side": "BUY" if self.radio_buy.isChecked() else "SELL",
            "quantity": self.spin_quantity.value(),
            "price": price
        }
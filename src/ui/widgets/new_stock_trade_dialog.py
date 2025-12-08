# src/ui/widgets/new_stock_trade_dialog.py

from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Optional, Literal, Dict, Any

from PyQt5.QtCore import Qt, QDate, QTime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLabel, QLineEdit, QRadioButton, QSpinBox, 
    QDateEdit, QTimeEdit, QPushButton, QMessageBox, 
    QStackedWidget, QWidget, QFrame
)

SideLiteral = Literal["BUY", "SELL"]

class NewStockTradeDialog(QDialog):
    """
    Yeni hisse/işlem ekleme sihirbazı.
    Adım 1: Hisse Seçimi ve Kontrolü (Fiyat/Ad getirme)
    Adım 2: İşlem (Trade) Detayları
    """
    def __init__(self, parent=None, price_lookup_func=None, lot_size: int = 1):
        super().__init__(parent)
        self.price_lookup_func = price_lookup_func
        self.lot_size = lot_size
        self.current_price: Optional[Decimal] = None
        self.fetched_stock_name: Optional[str] = None
        
        self._updating_amount = False
        self._updating_quantity = False

        self._init_ui()
        self._connect_signals()
        
        # Pencere ayarları
        self.setWindowTitle("Yeni İşlem Sihirbazı")
        self.setMinimumWidth(500)
        self.setFixedHeight(550)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        # Koyu tema arka planı
        self.setStyleSheet("background-color: #0f172a; color: #f8fafc;")

        # Başlangıçta 1. sayfayı göster
        self.stack.setCurrentIndex(0)
        self.line_ticker.setFocus()

    def _init_ui(self):
        # Ana Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- ÜST BİLGİ ŞERİDİ (HEADER) ---
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #1e293b; border-bottom: 1px solid #334155;")
        header_frame.setFixedHeight(70)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        self.lbl_step_title = QLabel("ADIM 1: Hisse Seçimi")
        self.lbl_step_title.setStyleSheet("color: #f8fafc; font-weight: bold; font-size: 16px;")
        
        self.lbl_step_indicator = QLabel("1 / 2")
        self.lbl_step_indicator.setStyleSheet("color: #94a3b8; font-weight: 500; font-size: 14px;")
        
        header_layout.addWidget(self.lbl_step_title)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_step_indicator)
        
        main_layout.addWidget(header_frame)

        # --- ORTA KISIM (SAYFALAR) ---
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # SAYFA 1: HİSSE SEÇİMİ
        self.page1 = QWidget()
        self._init_page1()
        self.stack.addWidget(self.page1)

        # SAYFA 2: İŞLEM DETAYLARI
        self.page2 = QWidget()
        self._init_page2()
        self.stack.addWidget(self.page2)

        # --- ALT BUTONLAR (FOOTER) ---
        footer_frame = QFrame()
        footer_frame.setStyleSheet("background-color: #0f172a; border-top: 1px solid #334155;")
        footer_frame.setFixedHeight(70)
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(20, 10, 20, 10)

        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton { color: #94a3b8; background: transparent; border: none; font-weight: 500; font-size: 14px; }
            QPushButton:hover { color: #f8fafc; }
        """)
        
        self.btn_back = QPushButton("Geri")
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.setVisible(False) # İlk sayfada gizli
        self.btn_back.setStyleSheet("""
            QPushButton { background-color: #334155; color: white; border-radius: 6px; padding: 8px 16px; font-weight: 600; }
            QPushButton:hover { background-color: #475569; }
        """)

        self.btn_next = QPushButton("Devam Et") # Sayfa 1'de Devam, Sayfa 2'de Kaydet olacak
        self.btn_next.setCursor(Qt.PointingHandCursor)
        # primaryButton stili
        self.btn_next.setStyleSheet("""
            QPushButton { background-color: #3b82f6; color: white; border-radius: 6px; padding: 8px 24px; font-weight: 600; font-size: 14px; }
            QPushButton:hover { background-color: #2563eb; }
        """)

        footer_layout.addWidget(self.btn_cancel)
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_back)
        footer_layout.addSpacing(10)
        footer_layout.addWidget(self.btn_next)

        main_layout.addWidget(footer_frame)

    def _init_page1(self):
        """1. Sayfa: Ticker girişi ve Fiyat Sorgulama"""
        layout = QVBoxLayout(self.page1)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Açıklama
        info = QLabel("İşlem yapmak istediğiniz hisse kodunu (Ticker) giriniz.\nBIST hisseleri için .IS uzantısı otomatik eklenecektir.")
        info.setStyleSheet("color: #94a3b8; font-size: 14px; line-height: 1.4;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Form
        form = QFormLayout()
        form.setVerticalSpacing(20)
        
        # Input Stilleri
        input_style = """
            QLineEdit { 
                background-color: #1e293b; 
                border: 1px solid #334155; 
                border-radius: 6px; 
                padding: 10px; 
                color: white; 
                font-size: 14px; 
            }
            QLineEdit:focus { border: 1px solid #3b82f6; }
        """

        self.line_ticker = QLineEdit()
        self.line_ticker.setPlaceholderText("Örn: ASELS, THYAO")
        self.line_ticker.setStyleSheet(input_style + "font-weight: bold; text-transform: uppercase;")
        
        self.line_name = QLineEdit()
        self.line_name.setPlaceholderText("Şirket adı (İsteğe bağlı)")
        self.line_name.setStyleSheet(input_style)

        lbl_ticker = QLabel("Hisse Kodu:")
        lbl_ticker.setStyleSheet("color: #cbd5e1; font-weight: 500;")
        lbl_name = QLabel("Şirket Adı:")
        lbl_name.setStyleSheet("color: #cbd5e1; font-weight: 500;")

        form.addRow(lbl_ticker, self.line_ticker)
        form.addRow(lbl_name, self.line_name)
        layout.addLayout(form)

        # Fiyat Bilgi Kartı (Sorgu Sonucu)
        self.price_info_frame = QFrame()
        self.price_info_frame.setStyleSheet("background-color: #1e293b; border-radius: 8px; border: 1px solid #334155;")
        self.price_info_frame.hide() # Başlangıçta gizli
        
        pi_layout = QVBoxLayout(self.price_info_frame)
        pi_layout.setContentsMargins(20, 15, 20, 15)
        
        lbl_info_title = QLabel("GÜNCEL PİYASA FİYATI")
        lbl_info_title.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold;")
        
        self.lbl_fetched_price = QLabel("-")
        self.lbl_fetched_price.setStyleSheet("color: #f8fafc; font-size: 28px; font-weight: bold;")
        
        self.lbl_fetched_source = QLabel("-")
        self.lbl_fetched_source.setStyleSheet("color: #22c55e; font-size: 13px;")
        
        pi_layout.addWidget(lbl_info_title)
        pi_layout.addWidget(self.lbl_fetched_price)
        pi_layout.addWidget(self.lbl_fetched_source)
        
        layout.addWidget(self.price_info_frame)
        layout.addStretch()

    def _init_page2(self):
        """2. Sayfa: Trade detayları"""
        layout = QVBoxLayout(self.page2)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Hisse Özeti (Hangi hissede işlem yapıyoruz?)
        self.lbl_summary_ticker = QLabel("ASELS.IS")
        self.lbl_summary_ticker.setStyleSheet("color: #3b82f6; font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        self.lbl_summary_ticker.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_summary_ticker)

        form = QFormLayout()
        form.setSpacing(15)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Input Style
        input_style = """
            QDateEdit, QTimeEdit, QSpinBox, QLineEdit {
                background-color: #1e293b; 
                border: 1px solid #334155; 
                border-radius: 6px; 
                padding: 8px;
                color: white;
                font-size: 14px;
            }
            QDateEdit::drop-down { border: none; }
        """
        self.page2.setStyleSheet(input_style)
        
        label_style = "color: #cbd5e1; font-weight: 500;"

        # Tarih / Saat
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.time_edit = QTimeEdit(QTime.currentTime())
        self.time_edit.setDisplayFormat("HH:mm")
        
        self._normalize_initial_datetime() # Haftasonu kontrolü

        lbl_date = QLabel("Tarih:")
        lbl_date.setStyleSheet(label_style)
        lbl_time = QLabel("Saat:")
        lbl_time.setStyleSheet(label_style)

        form.addRow(lbl_date, self.date_edit)
        form.addRow(lbl_time, self.time_edit)

        # İşlem Yönü
        side_layout = QHBoxLayout()
        self.radio_buy = QRadioButton("ALIŞ (Buy)")
        self.radio_sell = QRadioButton("SATIŞ (Sell)")
        self.radio_buy.setChecked(True)
        # Renklendirme
        radio_style = """
            QRadioButton { color: white; font-size: 14px; font-weight: 500; }
            QRadioButton::indicator:checked { border: 2px solid; border-radius: 6px; }
        """
        self.radio_buy.setStyleSheet(radio_style + "QRadioButton::indicator:checked { background-color: #22c55e; border-color: #22c55e; }")
        self.radio_sell.setStyleSheet(radio_style + "QRadioButton::indicator:checked { background-color: #ef4444; border-color: #ef4444; }")
        
        side_layout.addWidget(self.radio_buy)
        side_layout.addWidget(self.radio_sell)
        
        lbl_side = QLabel("İşlem Yönü:")
        lbl_side.setStyleSheet(label_style)
        form.addRow(lbl_side, side_layout)

        # Lot / Fiyat / Tutar
        self.spin_quantity = QSpinBox()
        self.spin_quantity.setRange(1, 10_000_000)
        self.spin_quantity.setValue(1)

        self.edit_price = QLineEdit()
        self.edit_price.setPlaceholderText("0.00")
        
        self.edit_amount = QLineEdit()
        self.edit_amount.setPlaceholderText("Toplam Tutar")

        lbl_lot = QLabel("Lot Adedi:")
        lbl_lot.setStyleSheet(label_style)
        lbl_price = QLabel("Birim Fiyat:")
        lbl_price.setStyleSheet(label_style)
        lbl_total = QLabel("Toplam Tutar:")
        lbl_total.setStyleSheet(label_style)

        form.addRow(lbl_lot, self.spin_quantity)
        form.addRow(lbl_price, self.edit_price)
        form.addRow(lbl_total, self.edit_amount)

        layout.addLayout(form)
        layout.addStretch()

    def _connect_signals(self):
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_next.clicked.connect(self._on_next_clicked)
        self.btn_back.clicked.connect(self._on_back_clicked)
        
        # Ticker değişince fiyatı sorgula
        self.line_ticker.editingFinished.connect(self._on_ticker_edited)
        
        # Hesaplamalar
        self.spin_quantity.valueChanged.connect(self._on_quantity_changed)
        self.edit_amount.textChanged.connect(self._on_amount_changed)
        
        # Tarih kontrolleri
        self.date_edit.dateChanged.connect(self._on_date_changed)
        self.time_edit.timeChanged.connect(self._on_time_changed)

    # --- SİHİRBAZ MANTIĞI ---

    def _on_next_clicked(self):
        current_idx = self.stack.currentIndex()
        
        if current_idx == 0:
            # Sayfa 1'den 2'ye geçiş
            if self._validate_page1():
                self._go_to_page2()
        else:
            # Sayfa 2'den Kaydet (Finish)
            if self._validate_page2():
                self.accept()

    def _on_back_clicked(self):
        # Sayfa 2'den 1'e dönüş
        self.stack.setCurrentIndex(0)
        self.btn_back.setVisible(False)
        self.btn_next.setText("Devam Et")
        self.lbl_step_title.setText("ADIM 1: Hisse Seçimi")
        self.lbl_step_indicator.setText("1 / 2")

    def _go_to_page2(self):
        # Sayfa 2'ye geçiş ayarları
        self.stack.setCurrentIndex(1)
        self.btn_back.setVisible(True)
        self.btn_next.setText("Kaydet ve Bitir")
        self.lbl_step_title.setText("ADIM 2: İşlem Detayları")
        self.lbl_step_indicator.setText("2 / 2")
        
        # Ticker'ı başlığa yaz
        ticker = self.line_ticker.text().upper().strip()
        if "." not in ticker: ticker += ".IS"
        name = self.line_name.text().strip() or self.fetched_stock_name or ""
        
        display_text = ticker
        if name:
            display_text += f"\n<span style='font-size:14px; color:#94a3b8; font-weight:normal;'>{name}</span>"
            
        self.lbl_summary_ticker.setText(display_text)
        
        # Fiyatı aktar (Eğer henüz girilmediyse)
        if self.current_price and not self.edit_price.text():
            self.edit_price.setText(str(self.current_price))
            # Lot 1 olduğu için tutarı da güncelle
            self.edit_amount.setText(f"{self.current_price:.2f}")

    # --- VALIDASYONLAR ---

    def _validate_page1(self) -> bool:
        ticker = self.line_ticker.text().strip()
        if not ticker:
            QMessageBox.warning(self, "Hata", "Lütfen bir hisse kodu (Ticker) giriniz.")
            return False
        
        # Fiyat sorgusu yapılmamışsa zorla yapalım
        if self.current_price is None:
            self._on_ticker_edited()
            # Eğer hala yoksa (bulunamadıysa)
            if self.current_price is None:
                # Kullanıcıya sor: Fiyatsız devam etsin mi?
                res = QMessageBox.question(self, "Fiyat Bulunamadı", 
                                           "Bu hisse için güncel fiyat çekilemedi. Yine de devam etmek ister misiniz?",
                                           QMessageBox.Yes | QMessageBox.No)
                if res == QMessageBox.No:
                    return False
        return True

    def _validate_page2(self) -> bool:
        # Fiyat ve Lot kontrolü
        try:
            p_text = self.edit_price.text().replace(",", ".")
            price = float(p_text) if p_text else 0.0
            if price <= 0: raise ValueError
        except:
            QMessageBox.warning(self, "Hata", "Geçerli bir fiyat giriniz.")
            return False
            
        # Tarih Gelecek Kontrolü
        if self.date_edit.date() > QDate.currentDate():
            QMessageBox.warning(self, "Hata", "Gelecek tarihli işlem girilemez.")
            return False
            
        return True

    # --- DATA TOPLAMA ---

    def get_result(self) -> Optional[Dict[str, Any]]:
        """Dialog başarıyla biterse veriyi dict olarak döner."""
        if self.result() != QDialog.Accepted:
            return None
            
        ticker = self.line_ticker.text().strip().upper()
        if "." not in ticker: ticker += ".IS"
        
        try:
            price = Decimal(self.edit_price.text().replace(",", "."))
        except:
            price = Decimal("0")

        return {
            "ticker": ticker,
            "name": self.line_name.text().strip() or ticker,
            "trade_date": self.date_edit.date().toPyDate(),
            "trade_time": self.time_edit.time().toPyTime(),
            "side": "BUY" if self.radio_buy.isChecked() else "SELL",
            "quantity": self.spin_quantity.value(),
            "price": price
        }

    # --- OLAYLAR (EVENTS) ---

    def _on_ticker_edited(self):
        ticker = self.line_ticker.text().strip().upper()
        if not ticker or not self.price_lookup_func:
            return

        result = self.price_lookup_func(ticker)
        if result:
            self.current_price = result.price
            
            # Fiyat bilgisini göster
            self.lbl_fetched_price.setText(f"₺ {result.price:,.2f}")
            source_text = "Anlık Veri (15dk gecikmeli olabilir)" if result.source == "intraday" else f"Kapanış ({result.as_of.strftime('%d.%m.%Y')})"
            self.lbl_fetched_source.setText(source_text)
            self.price_info_frame.show()
        else:
            self.current_price = None
            self.price_info_frame.hide()
            self.lbl_fetched_price.setText("-")

    def _on_quantity_changed(self, val):
        if self._updating_amount: return
        p_text = self.edit_price.text().replace(",", ".")
        if not p_text: return
        try:
            price = float(p_text)
            total = val * price
            self._updating_quantity = True
            self.edit_amount.setText(f"{total:.2f}")
            self._updating_quantity = False
        except: pass

    def _on_amount_changed(self, text):
        if self._updating_quantity: return
        p_text = self.edit_price.text().replace(",", ".")
        if not p_text: return
        try:
            price = float(p_text)
            amount = float(text.replace(",", "."))
            if price > 0:
                qty = int(amount / price)
                self._updating_amount = True
                self.spin_quantity.setValue(qty)
                self._updating_amount = False
        except: pass

    def _normalize_initial_datetime(self):
        now = QDate.currentDate()
        if now.dayOfWeek() > 5: # Haftasonu ise Cumaya çek
            now = now.addDays(-(now.dayOfWeek() - 5))
        self.date_edit.setDate(now)
        
        # Saat sınırları
        t = QTime.currentTime()
        if t.hour() < 10: t = QTime(10, 0)
        if t.hour() >= 18: t = QTime(17, 59)
        self.time_edit.setTime(t)

    def _on_date_changed(self, date):
        # Gelecek tarih kontrolü
        if date > QDate.currentDate():
            self.date_edit.setDate(QDate.currentDate())
        # Hafta sonu kontrolü
        elif date.dayOfWeek() > 5:
            self.date_edit.setDate(date.addDays(-1 if date.dayOfWeek()==6 else -2))
    
    def _on_time_changed(self, time):
        # Basit saat sınırı (10:00 - 18:00)
        if time.hour() < 10: self.time_edit.setTime(QTime(10, 0))
        elif time.hour() >= 18: self.time_edit.setTime(QTime(17, 59))
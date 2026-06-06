# src/ui/widgets/dashboard/dialogs/new_stock_trade_dialog.py

from __future__ import annotations
from src.ui.shared.locale_tr import L10N

from datetime import date, time
from decimal import Decimal
from typing import Optional, Literal, Dict, Any

from PyQt5.QtCore import Qt, QDate, QTime, QThreadPool
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLabel, QLineEdit, QRadioButton, QSpinBox, 
    QDateEdit, QTimeEdit, QPushButton, QMessageBox, 
    QStackedWidget, QWidget, QFrame
)
from src.ui.formatters import display_ticker
from src.ui.worker import Worker
from src.ui.widgets.dialog_behavior import configure_dialog_behavior
from src.ui.widgets.shared import CurrencySpinBox

SideLiteral = Literal["BUY", "SELL"]

class NewStockTradeDialog(QDialog):
    """
    Yeni hisse/işlem ekleme sihirbazı.
    Adım 1: Hisse Seçimi ve Kontrolü (Fiyat/Ad getirme)
    Adım 2: İşlem (Trade) Detayları
    """
    def __init__(self, parent=None, price_lookup_func=None, lot_size: int = 1):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.price_lookup_func = price_lookup_func
        self.lot_size = lot_size
        self.current_price: Optional[Decimal] = None
        self.fetched_stock_name: Optional[str] = None
        self._price_lookup_in_flight = False
        self._last_lookup_ticker: Optional[str] = None
        self._last_lookup_succeeded = False
        
        self._updating_amount = False
        self._updating_quantity = False

        self._init_ui()
        self._connect_signals()
        
        # Pencere ayarları
        self.setWindowTitle(L10N.YENI_ISLEM_SIHIRBAZI)
        self.setMinimumWidth(500)
        self.setFixedHeight(550)
        configure_dialog_behavior(self, self.btn_next, self._on_next_clicked)
        # Koyu tema arka planı
        self.setProperty("cssClass", "dialogContainer")

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
        header_frame.setProperty("cssClass", "dialogHeaderFrame")
        header_frame.setFixedHeight(70)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        self.lbl_step_title = QLabel(L10N.ADIM_1_HISSE_SECIMI)
        self.lbl_step_title.setProperty("cssClass", "dialogHeaderTitle")
        
        self.lbl_step_indicator = QLabel("1 / 2")
        self.lbl_step_indicator.setProperty("cssClass", "dialogStepIndicator")
        
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
        footer_frame.setProperty("cssClass", "dialogFooterFrame")
        footer_frame.setFixedHeight(70)
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(20, 10, 20, 10)

        self.btn_cancel = QPushButton(L10N.CANCEL)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setProperty("cssClass", "linkButton")
        
        self.btn_back = QPushButton(L10N.BACK)
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.setVisible(False) # İlk sayfada gizli
        self.btn_back.setProperty("cssClass", "secondaryButton")

        self.btn_next = QPushButton(L10N.DEVAM_ET) # Sayfa 1'de Devam, Sayfa 2'de Kaydet olacak
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setProperty("cssClass", "primaryButton")
        self.btn_next.setDefault(True)

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
        info.setProperty("cssClass", "dialogSubtitle")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Form
        form = QFormLayout()
        form.setVerticalSpacing(20)
        
        self.line_ticker = QLineEdit()
        self.line_ticker.setPlaceholderText(L10N.ORN_ASELS_THYAO)
        self.line_ticker.setProperty("cssClass", "tradeInputBold")
        
        self.lbl_company_name = QLabel(L10N.HISSE_KODU_GIRILDIGINDE_OTOMATIK_ALINACAK)
        self.lbl_company_name.setProperty("cssClass", "dialogSubtitle")
        self.lbl_company_name.setWordWrap(True)

        lbl_ticker = QLabel(L10N.HISSE_KODU)
        lbl_ticker.setProperty("cssClass", "formLabel")
        lbl_name = QLabel(L10N.SIRKET_ADI)
        lbl_name.setProperty("cssClass", "formLabel")

        form.addRow(lbl_ticker, self.line_ticker)
        form.addRow(lbl_name, self.lbl_company_name)
        layout.addLayout(form)

        # Fiyat Bilgi Kartı (Sorgu Sonucu)
        self.price_info_frame = QFrame()
        self.price_info_frame.setProperty("cssClass", "infoFrame")
        self.price_info_frame.hide() # Başlangıçta gizli
        
        pi_layout = QVBoxLayout(self.price_info_frame)
        pi_layout.setContentsMargins(20, 15, 20, 15)
        
        lbl_info_title = QLabel(L10N.GUNCEL_PIYASA_FIYATI)
        lbl_info_title.setProperty("cssClass", "infoTitle")
        
        self.lbl_fetched_price = QLabel("-")
        self.lbl_fetched_price.setProperty("cssClass", "priceLarge")
        
        self.lbl_fetched_source = QLabel("-")
        self.lbl_fetched_source.setProperty("cssClass", "successText")
        
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
        summary_widget = QWidget()
        summary_layout = QVBoxLayout(summary_widget)
        summary_layout.setContentsMargins(0, 0, 0, 12)
        summary_layout.setSpacing(2)

        self.lbl_summary_ticker = QLabel("ASELS")
        self.lbl_summary_ticker.setProperty("cssClass", "tradeSummaryTicker")
        self.lbl_summary_ticker.setAlignment(Qt.AlignCenter)
        self.lbl_summary_name = QLabel("")
        self.lbl_summary_name.setProperty("cssClass", "tradeSummaryName")
        self.lbl_summary_name.setAlignment(Qt.AlignCenter)

        summary_layout.addWidget(self.lbl_summary_ticker)
        summary_layout.addWidget(self.lbl_summary_name)
        layout.addWidget(summary_widget)

        form = QFormLayout()
        form.setSpacing(15)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)



        # Tarih / Saat
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setProperty("cssClass", "tradeInputNormal")
        self.time_edit = QTimeEdit(QTime.currentTime())
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setProperty("cssClass", "tradeInputNormal")
        
        self._normalize_initial_datetime() # Haftasonu kontrolü

        lbl_date = QLabel(L10N.TARIH_1)
        lbl_date.setProperty("cssClass", "formLabel")
        lbl_time = QLabel(L10N.SAAT)
        lbl_time.setProperty("cssClass", "formLabel")

        form.addRow(lbl_date, self.date_edit)
        form.addRow(lbl_time, self.time_edit)

        # İşlem Yönü
        side_layout = QHBoxLayout()
        self.radio_buy = QRadioButton(L10N.ALIS_BUY)
        self.radio_sell = QRadioButton(L10N.SATIS_SELL)
        self.radio_buy.setChecked(True)
        
        self.radio_buy.setProperty("cssClass", "tradeRadioBuy")
        self.radio_sell.setProperty("cssClass", "tradeRadioSell")
        
        side_layout.addWidget(self.radio_buy)
        side_layout.addWidget(self.radio_sell)
        
        lbl_side = QLabel(L10N.ISLEM_YONU)
        lbl_side.setProperty("cssClass", "formLabel")
        form.addRow(lbl_side, side_layout)

        # Lot / Fiyat / Tutar
        self.spin_quantity = QSpinBox()
        self.spin_quantity.setRange(1, 10_000_000)
        self.spin_quantity.setValue(1)
        self.spin_quantity.setProperty("cssClass", "tradeInputNormal")

        self.edit_price = CurrencySpinBox()
        self.edit_price.setRange(0, 1_000_000)
        self.edit_price.setDecimals(2)
        self.edit_price.setSuffix(" TL")
        self.edit_price.lineEdit().setPlaceholderText("0.00")
        self.edit_price.setProperty("cssClass", "tradeInputNormal")
        self.edit_price.setReadOnly(True)
        
        self.edit_amount = CurrencySpinBox()
        self.edit_amount.setRange(0, 1_000_000_000)
        self.edit_amount.setDecimals(2)
        self.edit_amount.setSuffix(" TL")
        self.edit_amount.lineEdit().setPlaceholderText(L10N.TOPLAM_TUTAR)
        self.edit_amount.setProperty("cssClass", "tradeInputNormal")
        self.edit_amount.setReadOnly(True)

        lbl_lot = QLabel(L10N.LOT_ADEDI)
        lbl_lot.setProperty("cssClass", "formLabel")
        lbl_price = QLabel(L10N.BIRIM_FIYAT)
        lbl_price.setProperty("cssClass", "formLabel")
        lbl_total = QLabel(L10N.TOPLAM_TUTAR_1)
        lbl_total.setProperty("cssClass", "formLabel")

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
        self.edit_amount.valueChanged.connect(self._on_amount_changed)
        
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
        self.btn_next.setText(L10N.DEVAM_ET)
        self.lbl_step_title.setText(L10N.ADIM_1_HISSE_SECIMI)
        self.lbl_step_indicator.setText("1 / 2")

    def _go_to_page2(self):
        # Sayfa 2'ye geçiş ayarları
        self.stack.setCurrentIndex(1)
        self.btn_back.setVisible(True)
        self.btn_next.setText(L10N.KAYDET_VE_BITIR)
        self.lbl_step_title.setText(L10N.ADIM_2_ISLEM_DETAYLARI)
        self.lbl_step_indicator.setText("2 / 2")
        
        # Ticker'ı başlığa yaz
        ticker = self._normalized_ticker()
        name = self.fetched_stock_name or ticker

        self.lbl_summary_ticker.setText(display_ticker(ticker))
        self.lbl_summary_name.setText(name)
        
        # Fiyatı aktar (Eğer henüz girilmediyse)
        if self.current_price and self.edit_price.value() <= 0:
            self.edit_price.setValue(float(self.current_price))
            # Lot 1 olduğu için tutarı da güncelle
            self.edit_amount.setValue(float(self.current_price))

    # --- VALIDASYONLAR ---

    def _validate_page1(self) -> bool:
        ticker = self.line_ticker.text().strip()
        if not ticker:
            QMessageBox.warning(self, L10N.ERROR, L10N.LUTFEN_BIR_HISSE_KODU_TICKER)
            return False

        current_ticker = self._normalized_ticker()
        if self._has_successful_lookup_for_ticker(current_ticker):
            return True

        if self._price_lookup_in_flight and self._last_lookup_ticker == current_ticker:
            return False

        if self.price_lookup_func and self._last_lookup_ticker != current_ticker:
            self._on_ticker_edited()
            return False

        if self.price_lookup_func and self._last_lookup_ticker == current_ticker and not self._last_lookup_succeeded:
            res = QMessageBox.question(
                self,
                L10N.FIYAT_BULUNAMADI,
                L10N.BU_HISSE_ICIN_GUNCEL_FIYAT,
                QMessageBox.Yes | QMessageBox.No,
            )
            if res == QMessageBox.No:
                return False
            return True

        return self.current_price is not None

    def _validate_page2(self) -> bool:
        # Fiyat ve Lot kontrolü
        try:
            price = self.edit_price.value()
            if price <= 0: raise ValueError
        except (ValueError, TypeError):
            QMessageBox.warning(self, L10N.ERROR, L10N.GECERLI_BIR_FIYAT_GIRINIZ)
            return False
            
        # Tarih Gelecek Kontrolü
        if self.date_edit.date() > QDate.currentDate():
            QMessageBox.warning(self, L10N.ERROR, L10N.GELECEK_TARIHLI_ISLEM_GIRILEMEZ)
            return False
            
        return True

    # --- DATA TOPLAMA ---

    def get_result(self) -> Optional[Dict[str, Any]]:
        """Dialog başarıyla biterse veriyi dict olarak döner."""
        if self.result() != QDialog.Accepted:
            return None
            
        ticker = self._normalized_ticker()
        
        try:
            price = self.edit_price.decimal_value()
        except (ValueError, Exception):
            price = Decimal("0")

        return {
            "ticker": ticker,
            "name": self.fetched_stock_name or ticker,
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

        normalized_ticker = self._normalize_ticker_value(ticker)
        if self._price_lookup_in_flight and normalized_ticker == self._last_lookup_ticker:
            return
        if self._has_successful_lookup_for_ticker(normalized_ticker):
            return

        self._begin_lookup(normalized_ticker)
        self.btn_next.setEnabled(False)
        self.btn_next.setText(L10N.BEKLENIYOR)
        self.lbl_fetched_price.setText(L10N.YUKLENIYOR)
        self.lbl_fetched_source.setText("")
        self.price_info_frame.show()

        worker = Worker(self.price_lookup_func, ticker)
        worker.signals.result.connect(
            lambda result, requested_ticker=normalized_ticker: self._on_price_fetched(result, requested_ticker)
        )
        worker.signals.error.connect(
            lambda err_tuple, requested_ticker=normalized_ticker: self._on_price_error(err_tuple, requested_ticker)
        )
        QThreadPool.globalInstance().start(worker)

    def _on_price_fetched(self, result, requested_ticker: Optional[str] = None):
        if requested_ticker is not None and requested_ticker != self._last_lookup_ticker:
            return

        self._price_lookup_in_flight = False
        if result:
            self.current_price = result.price
            self.lbl_fetched_price.setText(f"₺ {result.price:,.2f}")
            normalized_ticker = getattr(result, "normalized_ticker", None) or self._normalized_ticker()
            self.fetched_stock_name = getattr(result, "company_name", None) or normalized_ticker
            self.lbl_company_name.setText(self.fetched_stock_name)
            self._last_lookup_ticker = normalized_ticker
            self._last_lookup_succeeded = True
            source_text = (
                L10N.ANLIK_VERI_15DK_GECIKMELI_OLABILIR
                if result.source == "intraday"
                else f"Son Kapanış ({result.as_of.strftime('%d.%m.%Y')})"
            )
            self.lbl_fetched_source.setText(source_text)
        else:
            self._last_lookup_succeeded = False
            self.lbl_company_name.setText(L10N.SIRKET_ADI_ALINAMADI)
            self.lbl_fetched_price.setText("-")
            self.lbl_fetched_source.setText(L10N.FIYAT_BILGISI_BULUNAMADI)
            
        self.btn_next.setEnabled(True)
        self.btn_next.setText(L10N.DEVAM_ET)

    def _on_price_error(self, err_tuple, requested_ticker: Optional[str] = None):
        if requested_ticker is not None and requested_ticker != self._last_lookup_ticker:
            return

        self._price_lookup_in_flight = False
        self._last_lookup_succeeded = False
        self.lbl_company_name.setText(L10N.SIRKET_ADI_ALINAMADI)
        self.lbl_fetched_price.setText("-")
        self.lbl_fetched_source.setText(L10N.AG_HATASI)
        self.btn_next.setEnabled(True)
        self.btn_next.setText(L10N.DEVAM_ET)

    def _normalized_ticker(self) -> str:
        return self._normalize_ticker_value(self.line_ticker.text())

    @staticmethod
    def _normalize_ticker_value(ticker: str) -> str:
        normalized = (ticker or "").strip().upper()
        if normalized and "." not in normalized:
            normalized += ".IS"
        return normalized

    def _begin_lookup(self, normalized_ticker: str) -> None:
        self._price_lookup_in_flight = True
        self._last_lookup_ticker = normalized_ticker
        self._last_lookup_succeeded = False
        self.current_price = None
        self.fetched_stock_name = None
        self.lbl_company_name.setText(L10N.HISSE_KODU_GIRILDIGINDE_OTOMATIK_ALINACAK)
        self.edit_price.clear()
        self.edit_amount.clear()

    def _has_successful_lookup_for_ticker(self, normalized_ticker: str) -> bool:
        return (
            normalized_ticker == self._last_lookup_ticker
            and self._last_lookup_succeeded
            and self.current_price is not None
        )

    def _on_quantity_changed(self, val):
        if self._updating_amount: return
        if self.edit_price.value() <= 0: return
        try:
            price = self.edit_price.value()
            total = val * price
            self._updating_quantity = True
            self.edit_amount.setValue(total)
            self._updating_quantity = False
        except (ValueError, TypeError): pass

    def _on_amount_changed(self, amount):
        if self._updating_quantity: return
        if self.edit_price.value() <= 0: return
        try:
            price = self.edit_price.value()
            amount = float(amount or 0)
            if price > 0:
                qty = int(amount / price)
                self._updating_amount = True
                self.spin_quantity.setValue(qty)
                self._updating_amount = False
        except (ValueError, TypeError): pass

    def _normalize_initial_datetime(self):
        now = QDate.currentDate()
        self.date_edit.setDate(now)
        self.time_edit.setTime(QTime.currentTime())

    def _on_date_changed(self, date):
        # Gelecek tarih kontrolü
        if date > QDate.currentDate():
            self.date_edit.setDate(QDate.currentDate())
    
    def _on_time_changed(self, time):
        return

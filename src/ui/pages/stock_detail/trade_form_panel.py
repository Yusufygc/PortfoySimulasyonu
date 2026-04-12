# src/ui/pages/stock_detail/trade_form_panel.py

from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFormLayout, QDoubleSpinBox, 
    QSpinBox, QDateEdit, QButtonGroup
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from decimal import Decimal

class TradeFormPanel(QFrame):
    """Sağ paneldeki Alım/Satım işlemlerini yöneten form bileşeni."""
    
    # Kullanıcı emir girdiğinde fırlatılacak sinyal (formdan gelen bilgiler)
    trade_submitted = pyqtSignal(bool, int, float, QDate) # is_buy, qty, price, date
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("tradePanel")
        self.setFixedWidth(320)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QFrame#tradePanel {
                background-color: #1e293b;
                border-radius: 12px;
                border: 1px solid #334155;
            }
            QLabel { color: #cbd5e1; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        lbl_trade_title = QLabel("Hızlı İşlem")
        lbl_trade_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #f1f5f9;")
        layout.addWidget(lbl_trade_title)
        
        # Form
        form = QFormLayout()
        form.setSpacing(15)
        
        # İşlem Yönü (Segmented Control)
        side_layout = QHBoxLayout()
        side_layout.setSpacing(0)
        
        self.btn_buy_mode = QPushButton("ALIM")
        self.btn_buy_mode.setCheckable(True)
        self.btn_buy_mode.setChecked(True)
        
        self.btn_sell_mode = QPushButton("SATIŞ")
        self.btn_sell_mode.setCheckable(True)
        
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.btn_buy_mode)
        self.mode_group.addButton(self.btn_sell_mode)
        
        side_layout.addWidget(self.btn_buy_mode)
        side_layout.addWidget(self.btn_sell_mode)
        
        form.addRow("İşlem Yönü:", side_layout)
        
        # Adet
        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 1_000_000)
        self.spin_qty.setValue(1)
        self.spin_qty.setStyleSheet(self._get_input_style(16))
        form.addRow("Adet (Lot):", self.spin_qty)
        
        # Fiyat
        self.spin_price = QDoubleSpinBox()
        self.spin_price.setRange(0.01, 1_000_000)
        self.spin_price.setDecimals(2)
        self.spin_price.setSuffix(" ₺")
        self.spin_price.setStyleSheet(self._get_input_style(16))
        form.addRow("Fiyat:", self.spin_price)
        
        # Tarih
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setStyleSheet(self._get_input_style(14))
        form.addRow("Tarih:", self.date_edit)
        
        layout.addLayout(form)
        
        # Toplam Tutar Alanı
        total_layout = QHBoxLayout()
        self.lbl_total_amount = QLabel("Toplam: ₺ 0.00")
        self.lbl_total_amount.setStyleSheet("color: #f1f5f9; font-size: 16px; font-weight: bold;")
        self.lbl_total_amount.setAlignment(Qt.AlignCenter)
        total_layout.addWidget(self.lbl_total_amount)
        layout.addLayout(total_layout)
        
        # Etki Analizi (Impact Preview) Kartı
        self.impact_card = self._create_impact_card()
        layout.addWidget(self.impact_card)
        self.impact_card.setVisible(False)
        
        layout.addStretch()
        
        # Ana Aksiyon Butonu
        self.btn_trade = QPushButton("ALIM EMRİNİ ONAYLA")
        self.btn_trade.setFixedHeight(45)
        layout.addWidget(self.btn_trade)

        # Sinyaller
        self.btn_buy_mode.toggled.connect(self._update_trade_mode_ui)
        self.spin_qty.valueChanged.connect(self._on_input_changed)
        self.spin_price.valueChanged.connect(self._on_input_changed)
        self.btn_trade.clicked.connect(self._submit_trade)
        
        self._update_trade_mode_ui()

    def _get_input_style(self, font_size=14):
        return f"""
            background-color: #0f172a;
            color: #f1f5f9;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 8px;
            font-size: {font_size}px;
            font-weight: bold;
        """

    def _create_impact_card(self):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border-radius: 8px;
                border: 1px solid #334155;
            }
            QLabel { color: #cbd5e1; font-size: 13px; border: none; }
        """)
        lay = QVBoxLayout(card)
        lay.setSpacing(8)
        lay.setContentsMargins(15, 12, 15, 12)
        
        title = QLabel("İŞLEM ETKİSİ (Tahmini)")
        title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold; letter-spacing: 0.5px; border: none;")
        lay.addWidget(title)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #334155; border: none; margin-bottom: 5px;")
        line.setFixedHeight(1)
        lay.addWidget(line)

        self.impact_grid = QFormLayout()
        self.impact_grid.setSpacing(5)
        self.impact_grid.setContentsMargins(0, 5, 0, 0)
        lay.addLayout(self.impact_grid)
        return card

    def _update_trade_mode_ui(self):
        is_buy = self.btn_buy_mode.isChecked()
        
        base_style = """
            QPushButton {
                border: 1px solid #334155;
                font-weight: bold; font-size: 14px;
                color: #94a3b8; background-color: #0f172a;
                opacity: 0.5;
            }
        """
        active_style_buy = """
            QPushButton {
                background-color: rgba(16, 185, 129, 0.2);
                color: #10b981; border: 2px solid #10b981;
                font-weight: bold; font-size: 14px; outline: none;
            }
        """
        active_style_sell = """
            QPushButton {
                background-color: rgba(239, 68, 68, 0.2);
                color: #ef4444; border: 2px solid #ef4444;
                font-weight: bold; font-size: 14px; outline: none;
            }
        """
        
        self.btn_buy_mode.setStyleSheet(active_style_buy if is_buy else base_style + "border-top-left-radius: 8px; border-bottom-left-radius: 8px;")
        self.btn_sell_mode.setStyleSheet(active_style_sell if not is_buy else base_style + "border-top-right-radius: 8px; border-bottom-right-radius: 8px;")
        
        color = "#10b981" if is_buy else "#ef4444"
        text = "ALIM EMRİNİ ONAYLA" if is_buy else "SATIŞ EMRİNİ ONAYLA"
        self.btn_trade.setText(text)
        self.btn_trade.setStyleSheet(f"""
            QPushButton {{
                background-color: {color}; color: white;
                font-weight: bold; font-size: 16px;
                border-radius: 8px; border: none;
            }}
            QPushButton:hover {{ background-color: {color}; opacity: 0.9; }}
            QPushButton:pressed {{ background-color: {color}; opacity: 0.8; }}
        """)
        
        self.impact_preview_request()

    def _on_input_changed(self):
        qty = self.spin_qty.value()
        price = self.spin_price.value()
        total = Decimal(str(qty)) * Decimal(str(price))
        self.lbl_total_amount.setText(f"Toplam: ₺ {total:,.2f}")
        self.impact_preview_request()

    def impact_preview_request(self):
        # Üst sınıfa/Parent'a preview hesaplaması için çağrı, 
        # Ya da direkt burada hesaplanabilir eğer portföy servisi ve hisse verilmişse.
        # Bu bağımlılığı koparmak için bu sınıfta sadece arayüz bırakmalı.
        pass

    def update_impact_preview(self, portfolio_service, current_stock_id: int):
        """Bu fonksiyon dışarıdan (Orchestrator tarafından) çağrılarak preview render eder."""
        if not self.impact_card:
            return
            
        layout = self.impact_grid
        while layout.rowCount() > 0:
            layout.removeRow(0)
            
        is_buy = self.btn_buy_mode.isChecked()
        qty = int(self.spin_qty.value())
        price = Decimal(str(self.spin_price.value()))
        
        current_qty = 0
        current_avg = Decimal("0")
        
        if current_stock_id and portfolio_service:
            portfolio = portfolio_service.get_current_portfolio()
            pos = portfolio.positions.get(current_stock_id)
            if pos:
                current_qty = pos.total_quantity
                current_avg = pos.average_cost or Decimal("0")
        
        if is_buy:
            total_current_cost = current_qty * current_avg
            new_cost = qty * price
            total_new_qty = current_qty + qty
            new_avg_cost = (total_current_cost + new_cost) / total_new_qty if total_new_qty > 0 else 0
            
            self._add_impact_row("Yeni Ort. Maliyet", f"₺ {new_avg_cost:,.2f}", 
                               color="#fbbf24" if new_avg_cost != current_avg else "#f1f5f9")
            self._add_impact_row("Yeni Toplam Lot", f"{total_new_qty} (+{qty})")
            self._add_impact_row("İşlem Tutarı", f"₺ {new_cost:,.2f}")
        else:
            if qty > current_qty:
                self._add_impact_row("Uyarı", "Yetersiz Bakiye", color="#ef4444")
            else:
                realized_pl = (price - current_avg) * qty
                remaining_qty = current_qty - qty
                pl_color = "#10b981" if realized_pl >= 0 else "#ef4444"
                prefix = "+" if realized_pl >= 0 else ""
                self._add_impact_row("Tahmini K/Z", f"{prefix}₺ {realized_pl:,.2f}", color=pl_color)
                self._add_impact_row("Kalan Lot", f"{remaining_qty}")
                self._add_impact_row("Ort. Maliyet", f"₺ {current_avg:,.2f}")

        self.impact_card.setVisible(True)

    def _add_impact_row(self, label, value, color="#f1f5f9"):
        lbl_key = QLabel(label + ":")
        lbl_key.setStyleSheet("color: #94a3b8;")
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(f"color: {color}; font-weight: bold;")
        lbl_val.setAlignment(Qt.AlignRight)
        self.impact_grid.addRow(lbl_key, lbl_val)

    def _submit_trade(self):
        is_buy = self.btn_buy_mode.isChecked()
        qty = self.spin_qty.value()
        price = self.spin_price.value()
        date_sel = self.date_edit.date()
        self.trade_submitted.emit(is_buy, qty, price, date_sel)

    def set_price(self, price: float):
        self.spin_price.setValue(price)

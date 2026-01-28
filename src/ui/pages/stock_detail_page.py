from __future__ import annotations

from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import date, datetime, timedelta
import yfinance as yf

from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QFormLayout,
    QDoubleSpinBox,
    QSpinBox,
    QDateEdit,
    QSplitter,
    QWidget,
    QButtonGroup,
    QSpacerItem,
    QSizePolicy,
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QDate

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates

from .base_page import BasePage
from src.domain.models.trade import Trade, TradeSide

class StockDetailPage(BasePage):
    """
    Hisse Özet ve İşlem Sayfası.
    Dialogsuz, tek sayfa üzerinde analiz ve işlem.
    """

    def __init__(
        self,
        portfolio_service,
        stock_repo,
        price_lookup_func,
        parent=None,
    ):
        super().__init__(parent)
        self.page_title = "Hisse Detayı"
        self.portfolio_service = portfolio_service
        self.stock_repo = stock_repo
        self.price_lookup_func = price_lookup_func
        
        self.current_ticker: Optional[str] = None
        self.current_stock_id: Optional[int] = None
        self.current_price: Optional[Decimal] = None
        
        self._init_ui()

    def _init_ui(self):
        # Üst Header: Breadcrumb ve Ana Başlık
        top_layout = QVBoxLayout()
        top_layout.setSpacing(0)
        top_layout.setContentsMargins(0, 0, 0, 10)

        # Breadcrumb
        self.lbl_breadcrumb = QLabel("Portföy > ...")
        self.lbl_breadcrumb.setStyleSheet("color: #64748b; font-size: 12px; font-weight: bold;")
        top_layout.addWidget(self.lbl_breadcrumb)

        # Başlık Satırı: Ticker | İsim ............ Fiyat
        title_row = QHBoxLayout()
        title_row.setSpacing(15)

        self.lbl_ticker = QLabel("TICKER")
        self.lbl_ticker.setStyleSheet("color: #f1f5f9; font-size: 28px; font-weight: 900;")
        
        self.lbl_name = QLabel("Hisse Adı")
        self.lbl_name.setStyleSheet("color: #94a3b8; font-size: 18px; margin-top: 8px;")
        
        self.lbl_price = QLabel("₺ 0.00")
        self.lbl_price.setStyleSheet("color: #10b981; font-size: 32px; font-weight: bold;")
        
        title_row.addWidget(self.lbl_ticker)
        title_row.addWidget(self.lbl_name)
        title_row.addStretch()
        
        price_container = QVBoxLayout()
        price_label_caption = QLabel("Güncel Fiyat")
        price_label_caption.setAlignment(Qt.AlignRight)
        price_label_caption.setStyleSheet("color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;")
        
        price_container.addWidget(price_label_caption)
        price_container.addWidget(self.lbl_price)
        title_row.addLayout(price_container)

        top_layout.addLayout(title_row)
        self.main_layout.addLayout(top_layout)
        
        # Ayraç
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #334155; margin-bottom: 15px;")
        self.main_layout.addWidget(line)

        # Ana İçerik: Splitter (Sol: Grafik+İstatistik, Sağ: Al/Sat Formu)
        splitter = QSplitter(Qt.Horizontal)
        
        # --- SOL PANEL (Grafik ve İstatistikler) ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(15)
        
        # Grafik
        chart_frame = QFrame()
        # chart_frame.setMinimumHeight(200) # Gerekirse çok küçük olmasın diye
        chart_frame.setStyleSheet("background-color: #0f172a; border-radius: 8px;")
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        
        self.figure = Figure(figsize=(8, 5), facecolor='#0f172a')
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)
        
        # Grafik en fazla yeri kaplasın (Stretch: 3)
        left_layout.addWidget(chart_frame, 3)
        
        # İstatistik Kartları (Sıralama: Toplam Değer -> K/Z -> Maliyet -> Lot)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        # İstatistik Kartları (Sıralama: Toplam Değer -> K/Z -> Maliyet -> Lot)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        # Hero Metric: Toplam Değer
        self.card_total_val = self._create_stat_card("TOPLAM DEĞER", "₺ 0.00", icon="💰", is_hero=True)
        self.card_pl = self._create_stat_card("KAR / ZARAR", "₺ 0.00", is_colored=True, icon="📈")
        self.card_avg_cost = self._create_stat_card("ORT. MALİYET", "₺ 0.00", icon="🏷️")
        self.card_total_qty = self._create_stat_card("TOPLAM LOT", "0", icon="📦")
        
        stats_layout.addWidget(self.card_total_val, 2) # Hero daha geniş
        stats_layout.addWidget(self.card_pl, 1)
        stats_layout.addWidget(self.card_avg_cost)
        stats_layout.addWidget(self.card_total_qty)
        
        # Stats layout esnemesin, içeriği kadar yer kaplasın
        left_layout.addLayout(stats_layout)
        
        # İşlem Geçmişi Tablosu
        lbl_history = QLabel("İşlem Geçmişi")
        lbl_history.setStyleSheet("font-weight: bold; color: #94a3b8; font-size: 14px; margin-top: 10px;")
        
        # Label da esnemesin
        left_layout.addWidget(lbl_history)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["Tarih", "İşlem", "Adet", "Fiyat", "Tutar"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.verticalHeader().setVisible(False)
        # Tablo da esnesin ama grafik kadar değil (Stretch: 2)
        left_layout.addWidget(self.history_table, 2)
        
        # --- SAĞ PANEL (Al/Sat Formu) ---
        right_panel = QFrame()
        right_panel.setObjectName("tradePanel")
        right_panel.setFixedWidth(320)
        right_panel.setStyleSheet("""
            QFrame#tradePanel {
                background-color: #1e293b;
                border-radius: 12px;
                border: 1px solid #334155;
            }
            QLabel { color: #cbd5e1; }
        """)
        
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(15)
        
        lbl_trade_title = QLabel("Hızlı İşlem")
        lbl_trade_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #f1f5f9;")
        right_layout.addWidget(lbl_trade_title)
        
        # Form
        form = QFormLayout()
        form.setSpacing(15)
        
        # İşlem Yönü
        # İşlem Yönü (Segmented Control)
        side_layout = QHBoxLayout()
        side_layout.setSpacing(0)
        
        self.btn_buy_mode = QPushButton("AL (BUY)")
        self.btn_buy_mode.setCheckable(True)
        self.btn_buy_mode.setChecked(True)
        self.btn_buy_mode.setMinimumHeight(40)
        self.btn_buy_mode.setCursor(Qt.PointingHandCursor)
        
        self.btn_sell_mode = QPushButton("SAT (SELL)")
        self.btn_sell_mode.setCheckable(True)
        self.btn_sell_mode.setMinimumHeight(40)
        self.btn_sell_mode.setCursor(Qt.PointingHandCursor)
        
        self.side_group = QButtonGroup(self)
        self.side_group.addButton(self.btn_buy_mode)
        self.side_group.addButton(self.btn_sell_mode)
        
        self.side_group.buttonClicked.connect(self._update_trade_mode_ui)
        
        side_layout.addWidget(self.btn_buy_mode)
        side_layout.addWidget(self.btn_sell_mode)
        
        form.addRow("İşlem:", side_layout)
        
        # Stil tanımları için update çağırılacak - btn_trade'den sonra çağrılmalı
        # self._update_trade_mode_ui()
        
        # Adet
        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 1000000)
        self.spin_qty.setValue(1)
        self.spin_qty.setMinimumHeight(45)
        self.spin_qty.setStyleSheet(self._get_input_style(font_size=16))
        form.addRow("Lot:", self.spin_qty)
        
        # Gelişmiş Seçenekler (Toggle)
        self.btn_advanced = QPushButton("🛠️ Gelişmiş Seçenekler (Fiyat/Tarih)")
        self.btn_advanced.setCheckable(True)
        self.btn_advanced.setChecked(False)
        self.btn_advanced.setCursor(Qt.PointingHandCursor)
        self.btn_advanced.setStyleSheet("""
            QPushButton {
                color: #94a3b8;
                border: none;
                background: transparent;
                text-align: left;
                font-size: 12px;
                padding: 5px;
            }
            QPushButton:hover { color: #f1f5f9; }
            QPushButton:checked { color: #3b82f6; }
        """)
        self.btn_advanced.toggled.connect(self._toggle_advanced_options)
        form.addRow(self.btn_advanced)

        # Fiyat ve Tarih Container
        self.advanced_container = QWidget()
        advanced_layout = QFormLayout(self.advanced_container)
        advanced_layout.setContentsMargins(0,0,0,0)
        advanced_layout.setSpacing(15)

        # Fiyat
        self.spin_price = QDoubleSpinBox()
        self.spin_price.setRange(0.01, 1000000)
        self.spin_price.setDecimals(2)
        self.spin_price.setMinimumHeight(45)
        self.spin_price.setSuffix(" TL")
        self.spin_price.setStyleSheet(self._get_input_style())
        advanced_layout.addRow("Fiyat:", self.spin_price)
        
        # Tarih
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setMinimumHeight(45)
        self.date_edit.setStyleSheet(self._get_input_style())
        advanced_layout.addRow("Tarih:", self.date_edit)
        
        form.addRow(self.advanced_container)
        # Varsayılan gizli
        self.advanced_container.setVisible(False)
        
        right_layout.addLayout(form)
        
        # --- PRE-TRADE IMPACT PREVIEW ---
        self.impact_card = self._create_impact_card()
        right_layout.addWidget(self.impact_card)
        self.impact_card.setVisible(False) # Veriler gelene kadar gizli olabilir veya boş kalabilir
        
        # Sinyal bağlantıları (Tutar ve Impact güncelleme)
        self.spin_qty.valueChanged.connect(self._update_total_amount_label)
        self.spin_qty.valueChanged.connect(self._update_impact_preview)
        
        self.spin_price.valueChanged.connect(self._update_total_amount_label)
        self.spin_price.valueChanged.connect(self._update_impact_preview)

        
        # Tahmini Tutar
        self.lbl_total_amount = QLabel("Toplam: ₺ 0.00")
        self.lbl_total_amount.setStyleSheet("font-size: 16px; font-weight: bold; color: #f1f5f9; margin-top: 10px;")
        self.lbl_total_amount.setAlignment(Qt.AlignRight)
        right_layout.addWidget(self.lbl_total_amount)
        
        # Sinyal bağlantıları (Tutar güncelleme)
        self.spin_qty.valueChanged.connect(self._update_total_amount_label)
        self.spin_price.valueChanged.connect(self._update_total_amount_label)
        
        # Spacer ekle, butonu alta itmek için
        right_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        
        # İşlem Butonu
        self.btn_trade = QPushButton("EMRİ GÖNDER")
        self.btn_trade.setCursor(Qt.PointingHandCursor)
        self.btn_trade.setMinimumHeight(50)
        self.btn_trade.clicked.connect(self._on_submit_trade)
        self.btn_trade.clicked.connect(self._on_submit_trade)
        # Stil tanımlarını güncelle
        self._update_trade_mode_ui()
        
        right_layout.addWidget(self.btn_trade)
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([800, 350])
        
        self.main_layout.addWidget(splitter)

    def _toggle_advanced_options(self, checked):
        self.advanced_container.setVisible(checked)
        # Paneli yeniden boyutlandırmak gerekebilir ama layout otomatik halleder genelde

    def _create_stat_card(self, title, value, is_colored=False, icon="", is_hero=False):
        card = QFrame()
        bg_color = "#1e293b" if not is_hero else "#0f172a"
        border = "1px solid #334155" if not is_hero else "1px solid #3b82f6"
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color}; 
                border-radius: 12px;
                border: {border};
            }}
            QLabel {{ border: none; }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        
        header_layout = QHBoxLayout()
        lbl_title = QLabel(f"{icon} {title}")
        lbl_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold; text-transform: uppercase;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        lbl_val = QLabel(value)
        val_size = "20px" if not is_hero else "28px"
        lbl_val.setObjectName("valueLabel")
        if is_colored:
            # Renk ataması logic içinde yapılacak
            lbl_val.setStyleSheet(f"color: #f1f5f9; font-size: {val_size}; font-weight: bold;")
        else:
            val_color = "#f1f5f9" if not is_hero else "#3b82f6"
            lbl_val.setStyleSheet(f"color: {val_color}; font-size: {val_size}; font-weight: bold;")
            
        layout.addWidget(lbl_val)
        return card

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

    def _update_trade_mode_ui(self):
        is_buy = self.btn_buy_mode.isChecked()
        self._update_impact_preview()  # Mod değişince impact de değişir
        
        # Buton stilleri
        base_style = """
            QPushButton {
                border: 1px solid #334155;
                font-weight: bold;
                font-size: 14px;
                color: #94a3b8;
                background-color: #0f172a;
                opacity: 0.5;
            }
        """
        active_style_buy = """
            QPushButton {
                background-color: rgba(16, 185, 129, 0.2);
                color: #10b981;
                border: 2px solid #10b981;
                font-weight: bold;
                font-size: 14px;
                outline: none;
            }
        """
        active_style_sell = """
            QPushButton {
                background-color: rgba(239, 68, 68, 0.2);
                color: #ef4444;
                border: 2px solid #ef4444;
                font-weight: bold;
                font-size: 14px;
                outline: none;
            }
        """
        
        self.btn_buy_mode.setStyleSheet(active_style_buy if is_buy else base_style + "border-top-left-radius: 8px; border-bottom-left-radius: 8px;")
        self.btn_sell_mode.setStyleSheet(active_style_sell if not is_buy else base_style + "border-top-right-radius: 8px; border-bottom-right-radius: 8px;")
        
        # Ana aksiyon butonu güncelle
        color = "#10b981" if is_buy else "#ef4444"
        text = "ALIM EMRİNİ ONAYLA" if is_buy else "SATIŞ EMRİNİ ONAYLA"
        self.btn_trade.setText(text)
        self.btn_trade.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                font-weight: bold;
                font-size: 16px;
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {color};
                opacity: 0.9;
            }}
            QPushButton:pressed {{
                background-color: {color};
                opacity: 0.8;
            }}
        """)

    def _update_total_amount_label(self):
        qty = self.spin_qty.value()
        price = self.spin_price.value()
        total = Decimal(str(qty)) * Decimal(str(price))
        self.lbl_total_amount.setText(f"Toplam: ₺ {total:,.2f}")

    def set_stock(self, ticker: str, stock_id: Optional[int] = None):
        """Sayfayı belirli bir hisse için ayarlar."""
        self.current_ticker = ticker
        self.current_stock_id = stock_id
        
        # Hisse bilgilerini güncelle
        self.lbl_ticker.setText(ticker)
        self.lbl_breadcrumb.setText(f"PORTFÖY > {ticker}")
        
        if stock_id:
            stock = self.stock_repo.get_stock_by_id(stock_id)
            if stock:
                self.lbl_name.setText(stock.name or "")
        
        # Güncel fiyatı çek ve güncelle
        self._update_price_info()
        
        # İstatistikleri ve tabloyu yenile
        # İstatistikleri ve tabloyu yenile
        self.refresh_data()
        
        # Impact preview güncelle
        self._update_impact_preview()

    def refresh_data(self):
        if not self.current_ticker:
            return
            
        # 1. Grafiği çiz
        self._draw_chart()
        
        # 2. İstatistikleri hesapla
        self._calculate_stats()
        
        # 3. Geçmiş işlemleri yükle
        self._load_history()

    def _update_price_info(self):
        if not self.current_ticker or not self.price_lookup_func:
            return
            
        try:
            result = self.price_lookup_func(self.current_ticker)
            if result:
                self.current_price = result.price
                self.lbl_price.setText(f"₺ {self.current_price:,.2f}")
                
                # Alım formundaki fiyatı da güncelle (eğer kullanıcı değiştirmediyse pratik olur)
                self.spin_price.setValue(float(self.current_price))
        except Exception as e:
            print(f"Fiyat hatası: {e}")

    def _calculate_stats(self):
        if not self.current_stock_id:
            # Sadece ticker varsa ve işlem yoksa her şey sıfır
            return

        portfolio = self.portfolio_service.get_current_portfolio()
        position = portfolio.positions.get(self.current_stock_id)
        
        if position:
            avg_cost = position.average_cost or Decimal("0")
            total_qty = position.total_quantity
            total_cost = position.total_cost
            
            current_val = Decimal("0")
            if self.current_price:
                current_val = self.current_price * total_qty
            
            pl = current_val - total_cost
            
            # UI Güncelle
            self.card_avg_cost.findChild(QLabel, "valueLabel").setText(f"₺ {avg_cost:,.2f}")
            self.card_total_qty.findChild(QLabel, "valueLabel").setText(f"{total_qty}")
            self.card_total_val.findChild(QLabel, "valueLabel").setText(f"₺ {current_val:,.2f}")
            
            lbl_pl = self.card_pl.findChild(QLabel, "valueLabel")
            prefix = "▲" if pl >= 0 else "▼"
            lbl_pl.setText(f"{prefix} ₺ {abs(pl):,.2f}")
            lbl_pl.setStyleSheet(f"color: {'#10b981' if pl >= 0 else '#ef4444'}; font-size: 20px; font-weight: bold;")
        else:
            # Pozisyon yok veya kapatılmış
            self.card_avg_cost.findChild(QLabel, "valueLabel").setText("₺ 0.00")
            self.card_total_qty.findChild(QLabel, "valueLabel").setText("0")
            self.card_total_val.findChild(QLabel, "valueLabel").setText("₺ 0.00")
            self.card_pl.findChild(QLabel, "valueLabel").setText("₺ 0.00")

    def _load_history(self):
        if not self.current_stock_id:
            self.history_table.setRowCount(0)
            return

        trades = self.portfolio_service.get_trades_for_stock(self.current_stock_id)
        # Tarihe göre tersten sırala
        trades.sort(key=lambda t: t.trade_date, reverse=True)
        
        self.history_table.setRowCount(len(trades))
        for i, trade in enumerate(trades):
            self.history_table.setItem(i, 0, QTableWidgetItem(trade.trade_date.strftime("%d.%m.%Y")))
            
            type_str = "ALIM" if trade.side == TradeSide.BUY else "SATIM"
            item_type = QTableWidgetItem(type_str)
            item_type.setForeground(Qt.green if trade.side == TradeSide.BUY else Qt.red)
            self.history_table.setItem(i, 1, item_type)
            
            self.history_table.setItem(i, 2, QTableWidgetItem(str(trade.quantity)))
            self.history_table.setItem(i, 3, QTableWidgetItem(f"₺ {trade.price:,.2f}"))
            self.history_table.setItem(i, 3, QTableWidgetItem(f"₺ {trade.price:,.2f}"))
            self.history_table.setItem(i, 4, QTableWidgetItem(f"₺ {trade.total_amount:,.2f}"))
            
            # Hücreleri Read-Only Yap ve Stili Temizle
            for col in range(5):
                item = self.history_table.item(i, col)
                if item:
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    # Borderları kaldırarak daha temiz bir görünüm elde edebiliriz
                    item.setBackground(QColor("#1e293b" if i % 2 == 0 else "#0f172a")) # Zebra efekti manuel
                    
        # Tablo Stil İyileştirmesi
        # Tablo Stil İyileştirmesi
        self.history_table.setShowGrid(False)  # Gridleri tamamen kaldır
        self.history_table.setStyleSheet("""
            QTableWidget {
                background-color: #0f172a;
                border: none;
                gridline-color: transparent; 
                outline: none;
            }
            QTableWidget::item {
                padding: 10px;
                border: none;
                border-bottom: 1px solid #1e293b;
            }
            QTableWidget::item:selected {
                background-color: #334155;
                color: #f1f5f9;
            }
            QTableWidget::item:hover {
                background-color: #1e293b;
            }
            QHeaderView::section {
                background-color: #0f172a;
                color: #64748b;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #334155;
                font-weight: bold;
                text-transform: uppercase;
                font-size: 11px;
            }
        """)

    def _draw_chart(self):
        """Hisse fiyat grafiğini çiz."""
        if not self.current_ticker:
            return
            
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#0f172a')
        
        # Veri çek (son 1-2 yıl veya tümü)
        try:
            # Basitçe son 6 ayı çekelim
            end_date = date.today()
            start_date = end_date - timedelta(days=180) 
            
            yf_ticker = self.current_ticker if "." in self.current_ticker else f"{self.current_ticker}.IS"
            data = yf.download(yf_ticker, start=start_date, end=end_date + timedelta(days=1), progress=False, auto_adjust=False)
            
            if data is not None and not data.empty:
                close_col = 'Close' if 'Close' in data.columns else data.columns[0]
                
                # Pandas dataframe yapısı bazen karmaşık olabiliyor (MultiIndex)
                if hasattr(data[close_col], 'values') and len(data[close_col].shape) > 1:
                    close_data = data[close_col].iloc[:, 0]
                else:
                    close_data = data[close_col]
                    
                # Koyu tema için daha parlak mavi ve kalın çizgi
                ax.plot(data.index, close_data, color='#3b82f6', linewidth=2.5)
                ax.fill_between(data.index, close_data, alpha=0.1, color='#3b82f6')
                
                ax.set_title(f"{self.current_ticker} Fiyat Grafiği (Son 6 Ay)", color='#f1f5f9', fontsize=12)
                ax.grid(True, alpha=0.05, color='#f1f5f9')
                ax.tick_params(colors='#94a3b8')
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
                
                # Dinamik Y-Ekseni Ölçeklendirme
                ymin = close_data.min()
                ymax = close_data.max()
                padding = (ymax - ymin) * 0.1 if ymax > ymin else ymax * 0.1
                ax.set_ylim(max(0, ymin - padding), ymax + padding)

                # === ANALİTİK ÇİZGİLER ===
                
                # 1. Ort. Maliyet Çizgisi (Varsa)
                if self.current_stock_id:
                    portfolio = self.portfolio_service.get_current_portfolio()
                    pos = portfolio.positions.get(self.current_stock_id)
                    if pos and pos.average_cost:
                        ax.axhline(y=float(pos.average_cost), color='#f59e0b', linestyle='--', linewidth=1.0, alpha=0.7, label='Ort. Maliyet')

                # 2. Son Fiyat Çizgisi
                if self.current_price:
                    ax.axhline(y=float(self.current_price), color='#10b981', linestyle='-', linewidth=1, alpha=0.9, label=f'Güncel: {self.current_price:.2f}')

                ax.set_title(f"{self.current_ticker} - Fiyat Geçmişi", color='#f1f5f9', fontsize=14, fontweight='bold', pad=20)
                
                # Grid iyileştirme
                ax.grid(True, which='major', color='#f1f5f9', linestyle='-', alpha=0.05)
                ax.grid(True, which='minor', color='#f1f5f9', linestyle=':', alpha=0.02)
                ax.minorticks_on()
                
                ax.tick_params(axis='both', colors='#94a3b8', labelsize=10)
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))

                # Legend
                ax.legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f1f5f9', loc='upper left') 
                
                for spine in ax.spines.values():
                    spine.set_visible(False)
            else:
                ax.text(0.5, 0.5, "Veri bulunamadı", color='#94a3b8', ha='center', va='center')
                
        except Exception as e:
            print(f"Grafik hatası: {e}")
            ax.text(0.5, 0.5, "Grafik yüklenemedi", color='#94a3b8', ha='center', va='center')
            
        self.figure.tight_layout()
        self.canvas.draw()

    def _create_impact_card(self):
        """İşlem öncesi etki analizi kartı."""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border-radius: 8px;
                border: 1px solid #334155;
            }
            QLabel {
                color: #cbd5e1;
                font-size: 13px;
                border: none;
            }

        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 12, 15, 12)
        
        title = QLabel("İŞLEM ETKİSİ (Tahmini)")
        title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold; letter-spacing: 0.5px; border: none;")
        layout.addWidget(title)
        
        # Ayraç
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #334155; border: none; margin-bottom: 5px;")
        line.setFixedHeight(1)
        layout.addWidget(line)

        
        # Grid layout for details
        self.impact_grid = QFormLayout()
        self.impact_grid.setSpacing(5)
        self.impact_grid.setContentsMargins(0, 5, 0, 0)
        
        # Etiketler (Dinamik güncellenecek)
        self.lbl_impact_line1 = QLabel("...")
        self.lbl_impact_line2 = QLabel("...")
        self.lbl_impact_line3 = QLabel("...")
        
        # Style updates for values
        for lbl in [self.lbl_impact_line1, self.lbl_impact_line2, self.lbl_impact_line3]:
            lbl.setStyleSheet("font-weight: bold; color: #f1f5f9;")
            
        layout.addLayout(self.impact_grid)
        return card

    def _update_impact_preview(self):
        """Kullanıcı işlem yapmadan önce maliyet/kar tahminini göster."""
        if not self.impact_card:
            return
            
        # Varsayılan temizle
        layout = self.impact_grid
        while layout.rowCount() > 0:
            layout.removeRow(0)
            
        is_buy = self.btn_buy_mode.isChecked()
        qty = int(self.spin_qty.value())
        price = Decimal(str(self.spin_price.value()))
        
        # Mevcut pozisyon
        current_qty = 0
        current_avg = Decimal("0")
        
        if self.current_stock_id:
            portfolio = self.portfolio_service.get_current_portfolio()
            pos = portfolio.positions.get(self.current_stock_id)
            if pos:
                current_qty = pos.total_quantity
                current_avg = pos.average_cost or Decimal("0")
        
        if is_buy:
            # ALIM SENARYOSU: Yeni Maliyet Hesabı
            total_current_cost = current_qty * current_avg
            new_cost = qty * price
            
            total_new_qty = current_qty + qty
            new_avg_cost = (total_current_cost + new_cost) / total_new_qty if total_new_qty > 0 else 0
            
            self._add_impact_row("Yeni Ort. Maliyet", f"₺ {new_avg_cost:,.2f}", 
                               color="#fbbf24" if new_avg_cost != current_avg else "#f1f5f9")
            self._add_impact_row("Yeni Toplam Lot", f"{total_new_qty} (+{qty})")
            self._add_impact_row("İşlem Tutarı", f"₺ {new_cost:,.2f}")
            
        else:
            # SATIŞ SENARYOSU: Kar/Zarar Tahmini
            if qty > current_qty:
                self._add_impact_row("Uyarı", "Yetersiz Bakiye", color="#ef4444")
            else:
                realized_pl = (price - current_avg) * qty
                remaining_qty = current_qty - qty
                
                pl_color = "#10b981" if realized_pl >= 0 else "#ef4444"
                prefix = "+" if realized_pl >= 0 else ""
                
                self._add_impact_row("Tahmini K/Z", f"{prefix}₺ {realized_pl:,.2f}", color=pl_color)
                self._add_impact_row("Kalan Lot", f"{remaining_qty}")
                # Kısmi satışta ortalama maliyet değişmez (FIFO/Weighted Avg metoduna göre değişebilir ama genelde TRY muhasebesinde ağırlıklı ortalama satışla değişmez)
                self._add_impact_row("Ort. Maliyet", f"₺ {current_avg:,.2f} (Değişmez)")

        self.impact_card.setVisible(True)

    def _add_impact_row(self, label, value, color="#f1f5f9"):
        lbl_key = QLabel(label + ":")
        lbl_key.setStyleSheet("color: #94a3b8;")
        
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(f"color: {color}; font-weight: bold;")
        lbl_val.setAlignment(Qt.AlignRight)
        
        self.impact_grid.addRow(lbl_key, lbl_val)

    def _on_submit_trade(self):
        """İşlemi onayla ve kaydet."""
        if not self.current_ticker:
            return

        is_buy = self.btn_buy_mode.isChecked()
        side = TradeSide.BUY if is_buy else TradeSide.SELL
        
        qty = self.spin_qty.value()
        price = Decimal(str(self.spin_price.value()))
        trade_date = self.date_edit.date().toPyDate()
        
        # Eğer stock_id yoksa (yeni hisse), oluşturmamız lazım
        if not self.current_stock_id:
            # Hisseyi kaydet / bul
            try:
                # Stock Reposunda var mı?
                existing = self.stock_repo.get_stock_by_ticker(self.current_ticker)
                if existing:
                    self.current_stock_id = existing.id
                else:
                    # Yeni kaydet
                    from src.domain.models.stock import Stock
                    new_stock = Stock(id=None, ticker=self.current_ticker, name=self.current_ticker, currency_code="TRY")
                    saved = self.stock_repo.insert_stock(new_stock)
                    self.current_stock_id = saved.id
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Hisse kaydı yapılamadı: {e}")
                return

        # İşlemi oluştur
        try:
            if side == TradeSide.BUY:
                trade = Trade.create_buy(
                    stock_id=self.current_stock_id,
                    trade_date=trade_date,
                    trade_time=datetime.now().time(),
                    quantity=qty,
                    price=price
                )
            else:
                trade = Trade.create_sell(
                    stock_id=self.current_stock_id,
                    trade_date=trade_date,
                    trade_time=datetime.now().time(),
                    quantity=qty,
                    price=price
                )
            
            # Servise gönder
            self.portfolio_service.add_trade(trade)
            
            QMessageBox.information(self, "Başarılı", "İşlem başarıyla kaydedildi.")
            
            # Sayfayı yenile
            self.refresh_data()
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"İşlem hatası: {e}")

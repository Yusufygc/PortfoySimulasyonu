# src/ui/pages/analysis_page.py

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
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QDateEdit,
    QMessageBox,
    QFileDialog,
    QSplitter,
    QWidget,
    QAbstractItemView,
)
from PyQt5.QtCore import Qt, QDate

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from .base_page import BasePage


class AnalysisPage(BasePage):
    """
    Analiz sayfası - hisse performans grafikleri ve karşılaştırma.
    """

    # Grafik türleri
    CHART_PRICE = "Fiyat Grafiği"
    CHART_RETURNS = "Getiri Grafiği (%)"
    CHART_COMPARISON = "Normalize Karşılaştırma"
    CHART_PORTFOLIO_COST = "Portföy Dağılımı (Maliyet)"
    CHART_PORTFOLIO_VALUE = "Portföy Dağılımı (Güncel Değer)"

    def __init__(
        self,
        stock_repo,
        portfolio_service,
        price_repo,
        parent=None,
    ):
        super().__init__(parent)
        self.page_title = "Analiz"
        self.stock_repo = stock_repo
        self.portfolio_service = portfolio_service
        self.price_repo = price_repo
        
        self.price_cache: Dict[str, Any] = {}
        self.stock_first_trade_dates: Dict[int, date] = {}  # stock_id -> first_trade_date
        
        self._init_ui()

    def _init_ui(self):
        # Başlık
        header_layout = QHBoxLayout()
        lbl_title = QLabel("📈 Hisse Analizi")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #f1f5f9;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        
        self.btn_refresh = QPushButton("🔄 Verileri Güncelle")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self._on_refresh_data)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #f1f5f9;
                border: 1px solid #334155;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        header_layout.addWidget(self.btn_refresh)
        
        self.main_layout.addLayout(header_layout)

        # Ana içerik - Splitter
        splitter = QSplitter(Qt.Horizontal)

        # Sol Panel: Kontroller
        left_panel = QFrame()
        left_panel.setObjectName("analysisLeftPanel")
        left_panel.setFixedWidth(250)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(15, 15, 15, 15)
        left_layout.setSpacing(15)

        # Hisse Seçimi
        lbl_stocks = QLabel("Hisse Seç")
        lbl_stocks.setStyleSheet("font-weight: bold; color: #94a3b8; font-size: 13px;")
        left_layout.addWidget(lbl_stocks)

        self.stock_list = QListWidget()
        self.stock_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.stock_list.setAlternatingRowColors(True)
        self.stock_list.setMaximumHeight(200)
        self.stock_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.stock_list.setStyleSheet("""
            QListWidget {
                background-color: #1e293b;
                color: #f1f5f9;
                border: 1px solid #334155;
                border-radius: 6px;
            }
            QListWidget::item {
                padding: 6px;
            }
            QListWidget::item:selected {
                background-color: #3b82f6;
                color: white;
            }
            QListWidget::item:alternate {
                background-color: #0f172a;
            }
        """)
        left_layout.addWidget(self.stock_list)

        # Grafik Türü
        lbl_chart_type = QLabel("Grafik Türü")
        lbl_chart_type.setStyleSheet("font-weight: bold; color: #94a3b8; font-size: 13px;")
        left_layout.addWidget(lbl_chart_type)

        self.combo_chart_type = QComboBox()
        self.combo_chart_type.addItems([
            self.CHART_PRICE,
            self.CHART_RETURNS,
            self.CHART_COMPARISON,
            self.CHART_PORTFOLIO_COST,
            self.CHART_PORTFOLIO_VALUE,
        ])
        self.combo_chart_type.currentTextChanged.connect(self._on_chart_type_changed)
        self.combo_chart_type.setStyleSheet("""
            QComboBox {
                background-color: #1e293b;
                color: #f1f5f9;
                border: 1px solid #334155;
                padding: 8px 12px;
                border-radius: 6px;
                font-size: 13px;
            }
            QComboBox:hover {
                border-color: #3b82f6;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #94a3b8;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #f1f5f9;
                border: 1px solid #334155;
                selection-background-color: #3b82f6;
            }
        """)
        left_layout.addWidget(self.combo_chart_type)

        # Tarih Aralığı
        lbl_date_range = QLabel("Tarih Aralığı")
        lbl_date_range.setStyleSheet("font-weight: bold; color: #94a3b8; font-size: 13px;")
        left_layout.addWidget(lbl_date_range)

        date_layout = QVBoxLayout()
        date_layout.setSpacing(5)
        
        date_style = """
            QDateEdit {
                background-color: #1e293b;
                color: #f1f5f9;
                border: 1px solid #334155;
                padding: 6px 10px;
                border-radius: 6px;
            }
            QDateEdit:hover {
                border-color: #3b82f6;
            }
            QDateEdit::drop-down {
                border: none;
                width: 25px;
            }
            QDateEdit QAbstractItemView {
                background-color: #1e293b;
                color: #f1f5f9;
            }
        """
        
        lbl_start = QLabel("Başlangıç:")
        lbl_start.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate().addMonths(-1))
        self.date_start.dateChanged.connect(self._on_date_changed)
        self.date_start.setStyleSheet(date_style)
        date_layout.addWidget(lbl_start)
        date_layout.addWidget(self.date_start)
        
        lbl_end = QLabel("Bitiş:")
        lbl_end.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(QDate.currentDate())
        self.date_end.dateChanged.connect(self._on_date_changed)
        self.date_end.setStyleSheet(date_style)
        date_layout.addWidget(lbl_end)
        date_layout.addWidget(self.date_end)
        
        left_layout.addLayout(date_layout)

        # Hızlı tarih butonları
        quick_date_layout = QHBoxLayout()
        quick_date_layout.setSpacing(5)
        
        quick_btn_style = """
            QPushButton {
                background-color: #1e293b;
                color: #f1f5f9;
                border: 1px solid #334155;
                padding: 8px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3b82f6;
                border-color: #3b82f6;
            }
        """
        
        btn_1w = QPushButton("1H")
        btn_1w.setStyleSheet(quick_btn_style)
        btn_1w.clicked.connect(lambda: self._set_quick_date(7))
        
        btn_1m = QPushButton("1A")
        btn_1m.setStyleSheet(quick_btn_style)
        btn_1m.clicked.connect(lambda: self._set_quick_date(30))
        
        btn_3m = QPushButton("3A")
        btn_3m.setStyleSheet(quick_btn_style)
        btn_3m.clicked.connect(lambda: self._set_quick_date(90))
        
        btn_1y = QPushButton("1Y")
        btn_1y.setStyleSheet(quick_btn_style)
        btn_1y.clicked.connect(lambda: self._set_quick_date(365))
        
        btn_all = QPushButton("Tümü")
        btn_all.setStyleSheet(quick_btn_style)
        btn_all.clicked.connect(self._set_all_time)
        
        quick_date_layout.addWidget(btn_1w)
        quick_date_layout.addWidget(btn_1m)
        quick_date_layout.addWidget(btn_3m)
        quick_date_layout.addWidget(btn_1y)
        quick_date_layout.addWidget(btn_all)
        left_layout.addLayout(quick_date_layout)

        left_layout.addStretch()

        # Kaydet butonu
        self.btn_save = QPushButton("💾 Grafiği Kaydet")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self._on_save_chart)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                padding: 12px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        left_layout.addWidget(self.btn_save)

        # Sağ Panel: Grafik
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Matplotlib Figure
        self.figure = Figure(figsize=(10, 6), facecolor='#0f172a')
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("background-color: #1e293b; color: #f1f5f9;")

        right_layout.addWidget(self.toolbar)
        right_layout.addWidget(self.canvas)

        # Özet label
        self.lbl_summary = QLabel("Hisse seçin ve grafik oluşturun")
        self.lbl_summary.setStyleSheet("color: #94a3b8; padding: 10px; font-size: 13px;")
        right_layout.addWidget(self.lbl_summary)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([250, 800])

        self.main_layout.addWidget(splitter)

    def on_page_enter(self):
        self.refresh_data()

    def refresh_data(self):
        self._load_stock_first_trade_dates()
        self._load_stocks()
        self._update_chart()

    def _load_stock_first_trade_dates(self):
        """Her hisse için ilk işlem tarihini yükle."""
        self.stock_first_trade_dates.clear()
        try:
            trades = self.portfolio_service._portfolio_repo.get_all_trades()
            for trade in trades:
                stock_id = trade.stock_id
                trade_date = trade.trade_date
                if stock_id not in self.stock_first_trade_dates:
                    self.stock_first_trade_dates[stock_id] = trade_date
                else:
                    if trade_date < self.stock_first_trade_dates[stock_id]:
                        self.stock_first_trade_dates[stock_id] = trade_date
        except Exception as e:
            print(f"İlk işlem tarihleri yüklenemedi: {e}")

    def _get_earliest_trade_date(self) -> date:
        """Seçili hisseler için en erken işlem tarihini döner."""
        selected_items = self.stock_list.selectedItems()
        if not selected_items:
            # Tüm hisseler için en erken
            if self.stock_first_trade_dates:
                return min(self.stock_first_trade_dates.values())
            return date.today() - timedelta(days=30)
        
        earliest = date.today()
        for item in selected_items:
            stock_id = item.data(Qt.UserRole)
            if stock_id in self.stock_first_trade_dates:
                trade_date = self.stock_first_trade_dates[stock_id]
                if trade_date < earliest:
                    earliest = trade_date
        
        return earliest

    def _load_stocks(self):
        """Portföydeki hisseleri yükle."""
        self.stock_list.clear()
        
        portfolio = self.portfolio_service.get_current_portfolio()
        stock_ids = [p.stock_id for p in portfolio.positions.values() if p.total_quantity > 0]
        
        if stock_ids:
            ticker_map = self.stock_repo.get_ticker_map_for_stock_ids(stock_ids)
            for stock_id, ticker in ticker_map.items():
                item = QListWidgetItem(ticker)
                item.setData(Qt.UserRole, stock_id)
                self.stock_list.addItem(item)

    def _get_selected_tickers(self) -> List[str]:
        """Seçili hisselerin ticker'larını döner."""
        return [item.text() for item in self.stock_list.selectedItems()]

    def _get_selected_stock_ids(self) -> List[int]:
        """Seçili hisselerin stock_id'lerini döner."""
        return [item.data(Qt.UserRole) for item in self.stock_list.selectedItems()]

    def _on_selection_changed(self):
        self._update_chart()

    def _on_chart_type_changed(self, chart_type: str):
        self._update_chart()

    def _on_date_changed(self):
        self.price_cache.clear()
        self._update_chart()

    def _set_quick_date(self, days: int):
        """Hızlı tarih ayarla - hissenin alındığı günü dikkate al."""
        end_date = QDate.currentDate()
        
        # Seçili hisseler için en erken tarih
        earliest = self._get_earliest_trade_date()
        
        calculated_start = date.today() - timedelta(days=days)
        
        # Eğer hesaplanan tarih alım tarihinden önceyse, alım tarihini kullan
        if calculated_start < earliest:
            start_date = QDate(earliest.year, earliest.month, earliest.day)
        else:
            start_date = end_date.addDays(-days)
        
        self.date_start.setDate(start_date)
        self.date_end.setDate(end_date)

    def _set_all_time(self):
        """Tümü - hisse alındığından bugüne."""
        earliest = self._get_earliest_trade_date()
        start_date = QDate(earliest.year, earliest.month, earliest.day)
        end_date = QDate.currentDate()
        
        self.date_start.setDate(start_date)
        self.date_end.setDate(end_date)

    def _on_refresh_data(self):
        """Verileri yenile."""
        self.price_cache.clear()
        self._update_chart()
        QMessageBox.information(self, "Güncellendi", "Veriler yenilendi.")

    def _fetch_price_data(self, ticker: str, stock_id: Optional[int] = None) -> Optional[Any]:
        """yfinance ile fiyat verisi çek - alım tarihinden itibaren."""
        cache_key = f"{ticker}_{self.date_start.date().toString()}_{self.date_end.date().toString()}"
        if cache_key in self.price_cache:
            return self.price_cache[cache_key]

        yf_ticker = ticker if "." in ticker else f"{ticker}.IS"
        
        start = self.date_start.date().toPyDate()
        end = self.date_end.date().toPyDate() + timedelta(days=1)
        
        # Hissenin alım tarihini kontrol et
        if stock_id and stock_id in self.stock_first_trade_dates:
            first_trade = self.stock_first_trade_dates[stock_id]
            if start < first_trade:
                start = first_trade
        
        try:
            data = yf.download(yf_ticker, start=start, end=end, progress=False)
            if data is not None and not data.empty:
                self.price_cache[cache_key] = data
                return data
        except Exception as e:
            print(f"Veri çekilemedi: {ticker} - {e}")
        
        return None

    def _update_chart(self):
        """Grafiği güncelle."""
        chart_type = self.combo_chart_type.currentText()
        
        self.figure.clear()
        
        if chart_type == self.CHART_PORTFOLIO_COST:
            self._draw_portfolio_pie(mode="cost")
        elif chart_type == self.CHART_PORTFOLIO_VALUE:
            self._draw_portfolio_pie(mode="value")
        else:
            tickers = self._get_selected_tickers()
            stock_ids = self._get_selected_stock_ids()
            if not tickers:
                self._draw_empty_chart("Grafik için hisse seçin")
                return
            
            if chart_type == self.CHART_PRICE:
                self._draw_price_chart(tickers, stock_ids)
            elif chart_type == self.CHART_RETURNS:
                self._draw_returns_chart(tickers, stock_ids)
            elif chart_type == self.CHART_COMPARISON:
                self._draw_comparison_chart(tickers, stock_ids)
        
        self.canvas.draw()

    def _draw_empty_chart(self, message: str):
        """Boş grafik çiz."""
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#0f172a')
        ax.text(0.5, 0.5, message, ha='center', va='center', 
                fontsize=14, color='#94a3b8', transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        self.lbl_summary.setText(message)

    def _draw_price_chart(self, tickers: List[str], stock_ids: List[int]):
        """Fiyat grafiği çiz."""
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#0f172a')
        
        colors = plt.cm.tab10.colors
        valid_count = 0
        
        for i, (ticker, stock_id) in enumerate(zip(tickers, stock_ids)):
            data = self._fetch_price_data(ticker, stock_id)
            if data is not None and not data.empty:
                close_col = 'Close' if 'Close' in data.columns else data.columns[0]
                
                if hasattr(data[close_col], 'values') and len(data[close_col].shape) > 1:
                    close_data = data[close_col].iloc[:, 0]
                else:
                    close_data = data[close_col]
                
                ax.plot(data.index, close_data, label=ticker, 
                       color=colors[i % len(colors)], linewidth=2)
                valid_count += 1
        
        if valid_count == 0:
            self._draw_empty_chart("Veri bulunamadı")
            return
        
        ax.set_title("Fiyat Grafiği", color='#f1f5f9', fontsize=14, fontweight='bold')
        ax.set_xlabel("Tarih", color='#94a3b8')
        ax.set_ylabel("Fiyat (TL)", color='#94a3b8')
        ax.tick_params(colors='#94a3b8')
        ax.legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f1f5f9')
        ax.grid(True, alpha=0.3, color='#334155')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        
        for spine in ax.spines.values():
            spine.set_color('#334155')
        
        self.lbl_summary.setText(f"{valid_count} hisse gösteriliyor")

    def _draw_returns_chart(self, tickers: List[str], stock_ids: List[int]):
        """Getiri grafiği çiz (%)."""
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#0f172a')
        
        colors = plt.cm.tab10.colors
        valid_count = 0
        
        for i, (ticker, stock_id) in enumerate(zip(tickers, stock_ids)):
            data = self._fetch_price_data(ticker, stock_id)
            if data is not None and not data.empty:
                close_col = 'Close' if 'Close' in data.columns else data.columns[0]
                
                if hasattr(data[close_col], 'values') and len(data[close_col].shape) > 1:
                    close_data = data[close_col].iloc[:, 0]
                else:
                    close_data = data[close_col]
                
                returns = close_data.pct_change() * 100
                cumulative_returns = (1 + returns / 100).cumprod() * 100 - 100
                
                ax.plot(data.index, cumulative_returns, label=ticker,
                       color=colors[i % len(colors)], linewidth=2)
                valid_count += 1
        
        if valid_count == 0:
            self._draw_empty_chart("Veri bulunamadı")
            return
        
        ax.axhline(y=0, color='#ef4444', linestyle='--', alpha=0.5)
        ax.set_title("Kümülatif Getiri (%)", color='#f1f5f9', fontsize=14, fontweight='bold')
        ax.set_xlabel("Tarih", color='#94a3b8')
        ax.set_ylabel("Getiri (%)", color='#94a3b8')
        ax.tick_params(colors='#94a3b8')
        ax.legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f1f5f9')
        ax.grid(True, alpha=0.3, color='#334155')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        
        for spine in ax.spines.values():
            spine.set_color('#334155')
        
        self.lbl_summary.setText(f"{valid_count} hisse getiri karşılaştırması")

    def _draw_comparison_chart(self, tickers: List[str], stock_ids: List[int]):
        """Normalize karşılaştırma grafiği (100 bazlı)."""
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#0f172a')
        
        colors = plt.cm.tab10.colors
        valid_count = 0
        
        for i, (ticker, stock_id) in enumerate(zip(tickers, stock_ids)):
            data = self._fetch_price_data(ticker, stock_id)
            if data is not None and not data.empty:
                close_col = 'Close' if 'Close' in data.columns else data.columns[0]
                
                if hasattr(data[close_col], 'values') and len(data[close_col].shape) > 1:
                    close_data = data[close_col].iloc[:, 0]
                else:
                    close_data = data[close_col]
                
                normalized = (close_data / close_data.iloc[0]) * 100
                
                ax.plot(data.index, normalized, label=ticker,
                       color=colors[i % len(colors)], linewidth=2)
                valid_count += 1
        
        if valid_count == 0:
            self._draw_empty_chart("Veri bulunamadı")
            return
        
        ax.axhline(y=100, color='#94a3b8', linestyle='--', alpha=0.5)
        ax.set_title("Normalize Karşılaştırma (Başlangıç=100)", color='#f1f5f9', fontsize=14, fontweight='bold')
        ax.set_xlabel("Tarih", color='#94a3b8')
        ax.set_ylabel("Değer", color='#94a3b8')
        ax.tick_params(colors='#94a3b8')
        ax.legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f1f5f9')
        ax.grid(True, alpha=0.3, color='#334155')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        
        for spine in ax.spines.values():
            spine.set_color('#334155')
        
        self.lbl_summary.setText(f"{valid_count} hisse normalize karşılaştırma")

    def _draw_portfolio_pie(self, mode: str = "cost"):
        """Portföy dağılımı pasta grafiği - maliyet veya güncel değer bazlı."""
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#0f172a')
        
        portfolio = self.portfolio_service.get_current_portfolio()
        positions = [(p.stock_id, p.total_quantity, p.total_cost) 
                     for p in portfolio.positions.values() if p.total_quantity > 0]
        
        if not positions:
            self._draw_empty_chart("Portföyde pozisyon yok")
            return
        
        stock_ids = [p[0] for p in positions]
        ticker_map = self.stock_repo.get_ticker_map_for_stock_ids(stock_ids)
        
        labels = []
        values = []
        
        for pos in positions:
            stock_id, qty, cost = pos
            ticker = ticker_map.get(stock_id, "?")
            
            if mode == "cost":
                values.append(float(cost))
                labels.append(ticker)
            else:
                # Güncel değer hesapla
                data = self._fetch_price_data(ticker, stock_id)
                if data is not None and not data.empty:
                    close_col = 'Close' if 'Close' in data.columns else data.columns[0]
                    if hasattr(data[close_col], 'values') and len(data[close_col].shape) > 1:
                        last_price = float(data[close_col].iloc[-1, 0])
                    else:
                        last_price = float(data[close_col].iloc[-1])
                    current_value = last_price * qty
                    values.append(current_value)
                    labels.append(ticker)
                else:
                    # Veri yoksa maliyet kullan
                    values.append(float(cost))
                    labels.append(f"{ticker}*")
        
        if not values:
            self._draw_empty_chart("Değer hesaplanamadı")
            return
        
        colors = plt.cm.Set3.colors[:len(labels)]
        
        wedges, texts, autotexts = ax.pie(
            values, labels=labels, autopct='%1.1f%%',
            colors=colors, textprops={'color': '#f1f5f9', 'fontsize': 11}
        )
        
        for autotext in autotexts:
            autotext.set_color('#0f172a')
            autotext.set_fontweight('bold')
        
        title = "Portföy Dağılımı (Maliyet Bazlı)" if mode == "cost" else "Portföy Dağılımı (Güncel Değer)"
        ax.set_title(title, color='#f1f5f9', fontsize=14, fontweight='bold')
        
        total = sum(values)
        self.lbl_summary.setText(f"Toplam {len(positions)} pozisyon, ₺{total:,.2f}")

    def _on_save_chart(self):
        """Grafiği dosyaya kaydet."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Grafiği Kaydet",
            f"grafik_{date.today().strftime('%Y%m%d')}.png",
            "PNG Dosyası (*.png);;PDF Dosyası (*.pdf);;SVG Dosyası (*.svg)"
        )
        
        if not file_path:
            return
        
        try:
            self.figure.savefig(file_path, facecolor='#0f172a', edgecolor='none', 
                              bbox_inches='tight', dpi=150)
            QMessageBox.information(self, "Başarılı", f"Grafik kaydedildi:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Grafik kaydedilemedi:\n{e}")

# src/ui/pages/stock_detail/stock_detail_page.py

import logging
from typing import Optional
from decimal import Decimal
from datetime import datetime

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QMessageBox, QSplitter, QWidget
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QDate

from src.ui.pages.base_page import BasePage
from src.domain.models.trade import Trade, TradeSide

from .stock_chart_widget import StockChartWidget
from .stock_stats_panel import StockStatsPanel
from .trade_form_panel import TradeFormPanel

logger = logging.getLogger(__name__)

class StockDetailPage(BasePage):
    """
    Hisse Özet ve İşlem Sayfası (Orchestrator).
    Grafik, istatistikler ve al-sat formunu alt bileşenlerle yönetir.
    """

    def __init__(
        self,
        container,
        price_lookup_func,
        parent=None,
    ):
        super().__init__(parent)
        self.container = container
        self.page_title = "Hisse Detayı"
        self.portfolio_service = container.portfolio_service
        self.stock_repo = container.stock_repo
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

        self.lbl_breadcrumb = QLabel("Portföy > ...")
        self.lbl_breadcrumb.setStyleSheet("color: #64748b; font-size: 12px; font-weight: bold;")
        top_layout.addWidget(self.lbl_breadcrumb)

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
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #334155; margin-bottom: 15px;")
        self.main_layout.addWidget(line)

        # Splitter (Sol: Grafik+İst, Sağ: Form)
        splitter = QSplitter(Qt.Horizontal)
        
        # --- SOL PANEL ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(15)
        
        self.chart_widget = StockChartWidget()
        left_layout.addWidget(self.chart_widget, 3)
        
        self.stats_panel = StockStatsPanel()
        left_layout.addWidget(self.stats_panel)
        
        lbl_history = QLabel("İşlem Geçmişi")
        lbl_history.setStyleSheet("font-weight: bold; color: #94a3b8; font-size: 14px; margin-top: 10px;")
        left_layout.addWidget(lbl_history)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["Tarih", "İşlem", "Adet", "Fiyat", "Tutar"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.verticalHeader().setVisible(False)
        left_layout.addWidget(self.history_table, 2)
        
        # --- SAĞ PANEL ---
        self.trade_form = TradeFormPanel()
        
        # Sinyal bağlantıları
        self.trade_form.trade_submitted.connect(self._on_submit_trade)
        # Form güncellendiğinde preview update (bunu form içinden eventlerle bağlayabiliriz, fakat portfolio'ya erişim main'den)
        # Ancak valueChanged tetiklenmelerini dinleyip refresh atabiliriz
        self.trade_form.spin_qty.valueChanged.connect(self._trigger_impact_update)
        self.trade_form.spin_price.valueChanged.connect(self._trigger_impact_update)
        self.trade_form.btn_buy_mode.toggled.connect(self._trigger_impact_update)
        
        splitter.addWidget(left_panel)
        splitter.addWidget(self.trade_form)
        self.main_layout.addWidget(splitter)

    def _trigger_impact_update(self):
        self.trade_form.update_impact_preview(self.portfolio_service, self.current_stock_id)

    def set_stock(self, ticker: str, stock_id: Optional[int] = None):
        """Sayfayı belirli bir hisse için ayarlar."""
        self.current_ticker = ticker
        self.current_stock_id = stock_id
        
        self.lbl_ticker.setText(ticker)
        self.lbl_breadcrumb.setText(f"PORTFÖY > {ticker}")
        
        if stock_id:
            stock = self.stock_repo.get_stock_by_id(stock_id)
            if stock:
                self.lbl_name.setText(stock.name or "")
        
        self._update_price_info()
        self.refresh_data()
        self.trade_form.update_impact_preview(self.portfolio_service, self.current_stock_id)

    def refresh_data(self):
        if not self.current_ticker:
            return
            
        self.chart_widget.draw_chart(self.current_ticker, self.current_stock_id, self.current_price, self.portfolio_service)
        self.stats_panel.update_stats(self.portfolio_service, self.current_stock_id, self.current_price)
        self._load_history()

    def _update_price_info(self):
        if not self.current_ticker or not self.price_lookup_func:
            return
        try:
            result = self.price_lookup_func(self.current_ticker)
            if result:
                self.current_price = result.price
                self.lbl_price.setText(f"₺ {self.current_price:,.2f}")
                self.trade_form.set_price(float(self.current_price))
        except Exception as e:
            logger.error(f"Fiyat hatası: {e}")

    def _load_history(self):
        if not self.current_stock_id:
            self.history_table.setRowCount(0)
            return

        trades = self.portfolio_service.get_trades_for_stock(self.current_stock_id)
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
            self.history_table.setItem(i, 4, QTableWidgetItem(f"₺ {trade.total_amount:,.2f}"))
            
            for col in range(5):
                item = self.history_table.item(i, col)
                if item:
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    item.setBackground(QColor("#1e293b" if i % 2 == 0 else "#0f172a"))
                    
        self.history_table.setShowGrid(False)
        self.history_table.setStyleSheet("""
            QTableWidget {
                background-color: #0f172a; border: none; gridline-color: transparent; outline: none;
            }
            QTableWidget::item { padding: 10px; border: none; border-bottom: 1px solid #1e293b; }
            QTableWidget::item:selected { background-color: #334155; color: #f1f5f9; }
            QTableWidget::item:hover { background-color: #1e293b; }
            QHeaderView::section {
                background-color: #0f172a; color: #64748b; padding: 8px; border: none;
                border-bottom: 2px solid #334155; font-weight: bold; text-transform: uppercase; font-size: 11px;
            }
        """)

    def _on_submit_trade(self, is_buy: bool, qty: int, price: float, date_sel: QDate):
        if not self.current_ticker:
            return

        side = TradeSide.BUY if is_buy else TradeSide.SELL
        trade_date = date_sel.toPyDate()
        decimal_price = Decimal(str(price))
        
        if not self.current_stock_id:
            try:
                existing = self.stock_repo.get_stock_by_ticker(self.current_ticker)
                if existing:
                    self.current_stock_id = existing.id
                else:
                    from src.domain.models.stock import Stock
                    new_stock = Stock(id=None, ticker=self.current_ticker, name=self.current_ticker, currency_code="TRY")
                    saved = self.stock_repo.insert_stock(new_stock)
                    self.current_stock_id = saved.id
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Hisse kaydı yapılamadı: {e}")
                return

        try:
            if side == TradeSide.BUY:
                trade = Trade.create_buy(
                    stock_id=self.current_stock_id, trade_date=trade_date,
                    trade_time=datetime.now().time(), quantity=qty, price=decimal_price
                )
            else:
                trade = Trade.create_sell(
                    stock_id=self.current_stock_id, trade_date=trade_date,
                    trade_time=datetime.now().time(), quantity=qty, price=decimal_price
                )
            
            self.portfolio_service.add_trade(trade)
            QMessageBox.information(self, "Başarılı", "İşlem başarıyla kaydedildi.")
            self.refresh_data()
            self.trade_form.update_impact_preview(self.portfolio_service, self.current_stock_id)
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"İşlem hatası: {e}")

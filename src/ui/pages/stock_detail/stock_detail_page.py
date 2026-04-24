import logging
from decimal import Decimal
from typing import Optional

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from src.domain.models.trade import TradeSide
from src.ui.pages.base_page import BasePage

from .stock_chart_widget import StockChartWidget
from .stock_stats_panel import StockStatsPanel
from .trade_form_panel import TradeFormPanel

logger = logging.getLogger(__name__)


class StockDetailPage(BasePage):
    def __init__(
        self,
        container,
        price_lookup_func,
        parent=None,
    ):
        super().__init__(parent)
        self.container = container
        self.page_title = "Hisse Detayi"
        self.portfolio_service = container.portfolio_service
        self.stock_repo = container.stock_repo
        self.trade_entry_service = container.trade_entry_service
        self.price_lookup_func = price_lookup_func

        self.current_ticker: Optional[str] = None
        self.current_stock_id: Optional[int] = None
        self.current_price: Optional[Decimal] = None
        self._init_ui()

    def _init_ui(self):
        top_layout = QVBoxLayout()
        top_layout.setSpacing(0)
        top_layout.setContentsMargins(0, 0, 0, 10)

        self.lbl_breadcrumb = QLabel("Portfoy > ...")
        self.lbl_breadcrumb.setProperty("cssClass", "breadcrumbText")
        top_layout.addWidget(self.lbl_breadcrumb)

        title_row = QHBoxLayout()
        title_row.setSpacing(15)

        self.lbl_ticker = QLabel("TICKER")
        self.lbl_ticker.setProperty("cssClass", "stockTitleLarge")
        self.lbl_name = QLabel("Hisse Adi")
        self.lbl_name.setProperty("cssClass", "stockSubtitle")
        self.lbl_price = QLabel("TL 0.00")
        self.lbl_price.setProperty("cssClass", "stockPriceCurrent")

        title_row.addWidget(self.lbl_ticker)
        title_row.addWidget(self.lbl_name)
        title_row.addStretch()

        price_container = QVBoxLayout()
        price_label_caption = QLabel("Guncel Fiyat")
        price_label_caption.setAlignment(Qt.AlignRight)
        price_label_caption.setProperty("cssClass", "stockPriceCaption")
        price_container.addWidget(price_label_caption)
        price_container.addWidget(self.lbl_price)
        title_row.addLayout(price_container)

        top_layout.addLayout(title_row)
        self.main_layout.addLayout(top_layout)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setProperty("cssClass", "horizontalDivider")
        self.main_layout.addWidget(line)

        splitter = QSplitter(Qt.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(15)

        self.chart_widget = StockChartWidget()
        left_layout.addWidget(self.chart_widget, 3)

        self.stats_panel = StockStatsPanel()
        left_layout.addWidget(self.stats_panel)

        lbl_history = QLabel("Islem Gecmisi")
        lbl_history.setProperty("cssClass", "panelTitle")
        left_layout.addWidget(lbl_history)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["Tarih", "Islem", "Adet", "Fiyat", "Tutar"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.verticalHeader().setVisible(False)
        left_layout.addWidget(self.history_table, 2)

        self.trade_form = TradeFormPanel()
        self.trade_form.trade_submitted.connect(self._on_submit_trade)
        self.trade_form.spin_qty.valueChanged.connect(self._trigger_impact_update)
        self.trade_form.spin_price.valueChanged.connect(self._trigger_impact_update)
        self.trade_form.btn_buy_mode.toggled.connect(self._trigger_impact_update)

        splitter.addWidget(left_panel)
        splitter.addWidget(self.trade_form)
        self.main_layout.addWidget(splitter)

    def _trigger_impact_update(self):
        self.trade_form.update_impact_preview(self.portfolio_service, self.current_stock_id)

    def set_stock(self, ticker: str, stock_id: Optional[int] = None):
        self.current_ticker = ticker
        self.current_stock_id = stock_id
        self.lbl_ticker.setText(ticker)
        self.lbl_breadcrumb.setText(f"PORTFOY > {ticker}")

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
        self.chart_widget.draw_chart(
            self.current_ticker,
            self.current_stock_id,
            self.current_price,
            self.portfolio_service,
        )
        self.stats_panel.update_stats(self.portfolio_service, self.current_stock_id, self.current_price)
        self._load_history()

    def _update_price_info(self):
        if not self.current_ticker or not self.price_lookup_func:
            return
        try:
            result = self.price_lookup_func(self.current_ticker)
            if result:
                self.current_price = result.price
                self.lbl_price.setText(f"TL {self.current_price:,.2f}")
                self.trade_form.set_price(float(self.current_price))
        except Exception as exc:
            logger.error("Fiyat hatasi: %s", exc)

    def _load_history(self):
        if not self.current_stock_id:
            self.history_table.setRowCount(0)
            return

        trades = self.portfolio_service.get_trades_for_stock(self.current_stock_id)
        trades.sort(key=lambda trade: trade.trade_date, reverse=True)

        self.history_table.setRowCount(len(trades))
        for row_index, trade in enumerate(trades):
            self.history_table.setItem(row_index, 0, QTableWidgetItem(trade.trade_date.strftime("%d.%m.%Y")))
            type_str = "ALIM" if trade.side == TradeSide.BUY else "SATIM"
            type_item = QTableWidgetItem(type_str)
            type_item.setForeground(Qt.green if trade.side == TradeSide.BUY else Qt.red)
            self.history_table.setItem(row_index, 1, type_item)
            self.history_table.setItem(row_index, 2, QTableWidgetItem(str(trade.quantity)))
            self.history_table.setItem(row_index, 3, QTableWidgetItem(f"TL {trade.price:,.2f}"))
            self.history_table.setItem(row_index, 4, QTableWidgetItem(f"TL {trade.total_amount:,.2f}"))

            for col in range(5):
                item = self.history_table.item(row_index, col)
                if item:
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    item.setBackground(QColor("#1e293b" if row_index % 2 == 0 else "#0f172a"))

        self.history_table.setShowGrid(False)
        self.history_table.setProperty("cssClass", "dataTable")

    def _on_submit_trade(self, is_buy: bool, qty: int, price: float, date_sel: QDate):
        if not self.current_ticker:
            return

        trade_side = TradeSide.BUY if is_buy else TradeSide.SELL
        try:
            result = self.trade_entry_service.submit_trade(
                ticker=self.current_ticker,
                stock_id=self.current_stock_id,
                side=trade_side,
                quantity=qty,
                price=Decimal(str(price)),
                trade_date=date_sel.toPyDate(),
                name=self.current_ticker,
            )
            self.current_stock_id = result.stock_id
            self.current_ticker = result.ticker
            QMessageBox.information(self, "Basarili", "Islem basariyla kaydedildi.")
            self.refresh_data()
            self.trade_form.update_impact_preview(self.portfolio_service, self.current_stock_id)
        except Exception as exc:
            QMessageBox.critical(self, "Hata", f"Islem hatasi: {exc}")

# src/ui/pages/analysis/analysis_page.py

import logging
import pandas as pd
import yfinance as yf
from datetime import date, timedelta
from typing import Dict, Any, Optional

from PyQt5.QtWidgets import (
    QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QFileDialog, QSplitter
)
from PyQt5.QtCore import Qt, QSize
from src.ui.core.icon_manager import IconManager

from src.ui.pages.base_page import BasePage
from .analysis_filter_panel import AnalysisFilterPanel
from .analysis_chart_engine import AnalysisChartEngine

logger = logging.getLogger(__name__)

class AnalysisPage(BasePage):
    """
    Analiz sayfası Orchestrator.
    Filtre panelinden gelen bilgilere göre portföy ve veri servislerinden bilgileri çeker,
    uygun formatta DataFrame'lere çevirip çizim motoruna aktarır.
    """

    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container
        self.page_title = "Analiz"
        self.stock_repo = container.stock_repo
        self.portfolio_service = container.portfolio_service
        self.price_repo = container.price_repo
        
        self.price_cache: Dict[str, Any] = {}
        self.stock_first_trade_dates: Dict[int, date] = {}
        
        self._init_ui()

    def _init_ui(self):
        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(IconManager.get_icon("line-chart", color="@COLOR_ACCENT", size=QSize(28, 28)).pixmap(28, 28))
        header_layout.addWidget(icon_lbl)
        
        lbl_title = QLabel("Hisse Analizi")
        lbl_title.setProperty("cssClass", "pageTitle")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        
        self.btn_refresh = QPushButton("Verileri Güncelle")
        self.btn_refresh.setIcon(IconManager.get_icon("refresh-cw", color="@COLOR_TEXT_WHITE"))
        self.btn_refresh.setIconSize(QSize(18, 18))
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self._on_refresh_data)
        self.btn_refresh.setProperty("cssClass", "secondaryButton")
        header_layout.addWidget(self.btn_refresh)
        
        self.main_layout.addLayout(header_layout)

        # Body - Splitter
        splitter = QSplitter(Qt.Horizontal)

        # Filters
        self.filter_panel = AnalysisFilterPanel()
        self.filter_panel.set_earliest_date_calculator(self._get_earliest_trade_date)
        self.filter_panel.filter_changed.connect(self._update_chart)
        self.filter_panel.save_requested.connect(self._on_save_chart)

        # Chart Engine
        self.chart_engine = AnalysisChartEngine()

        splitter.addWidget(self.filter_panel)
        splitter.addWidget(self.chart_engine)
        splitter.setSizes([250, 800])

        self.main_layout.addWidget(splitter)

    def on_page_enter(self):
        self.refresh_data()

    def refresh_data(self):
        self._load_stock_first_trade_dates()
        self._load_stocks()
        self._update_chart()

    def _load_stock_first_trade_dates(self):
        self.stock_first_trade_dates.clear()
        try:
            trades = self.portfolio_service.get_all_trades()
            for trade in trades:
                stock_id = trade.stock_id
                trade_date = trade.trade_date
                if stock_id not in self.stock_first_trade_dates:
                    self.stock_first_trade_dates[stock_id] = trade_date
                else:
                    if trade_date < self.stock_first_trade_dates[stock_id]:
                        self.stock_first_trade_dates[stock_id] = trade_date
        except Exception as e:
            logger.error(f"İlk işlem tarihleri yüklenemedi: {e}", exc_info=True)

    def _get_earliest_trade_date(self) -> date:
        selected_ids = self.filter_panel.get_selected_stock_ids()
        if not selected_ids:
            if self.stock_first_trade_dates:
                return min(self.stock_first_trade_dates.values())
            return date.today() - timedelta(days=30)
        
        earliest = date.today()
        for idx in selected_ids:
            if idx in self.stock_first_trade_dates:
                trade_date = self.stock_first_trade_dates[idx]
                if trade_date < earliest:
                    earliest = trade_date
        return earliest

    def _load_stocks(self):
        portfolio = self.portfolio_service.get_current_portfolio()
        stock_ids = [p.stock_id for p in portfolio.positions.values() if p.total_quantity > 0]
        
        if stock_ids:
            ticker_map = self.stock_repo.get_ticker_map_for_stock_ids(stock_ids)
            self.filter_panel.set_stocks(ticker_map)

    def _on_refresh_data(self):
        self.price_cache.clear()
        self._update_chart()
        QMessageBox.information(self, "Güncellendi", "Veriler yenilendi.")

    def _fetch_price_data(self, ticker: str, stock_id: Optional[int] = None) -> Optional[pd.DataFrame]:
        start_dt, end_dt = self.filter_panel.get_date_range()
        cache_key = f"{ticker}_{start_dt}_{end_dt}"
        if cache_key in self.price_cache:
            return self.price_cache[cache_key]

        yf_ticker = ticker if "." in ticker else f"{ticker}.IS"
        
        if stock_id and stock_id in self.stock_first_trade_dates:
            first_trade = self.stock_first_trade_dates[stock_id]
            if start_dt < first_trade:
                start_dt = first_trade
        
        try:
            data = yf.download(yf_ticker, start=start_dt, end=end_dt + timedelta(days=1), progress=False)
            if data is not None and not data.empty:
                self.price_cache[cache_key] = data
                return data
        except Exception as e:
            logger.error(f"Veri çekilemedi: {ticker} - {e}", exc_info=True)
        return None

    def _update_chart(self):
        chart_type = self.filter_panel.get_chart_type()
        
        if chart_type == AnalysisFilterPanel.CHART_PORTFOLIO_COST:
            self._render_pie_chart("cost")
        elif chart_type == AnalysisFilterPanel.CHART_PORTFOLIO_VALUE:
            self._render_pie_chart("value")
        else:
            tickers = self.filter_panel.get_selected_tickers()
            stock_ids = self.filter_panel.get_selected_stock_ids()
            if not tickers:
                self.chart_engine.draw_empty_chart("Grafik için hisse seçin")
                return
            
            data_map = {}
            for t, s in zip(tickers, stock_ids):
                df = self._fetch_price_data(t, s)
                if df is not None:
                    data_map[t] = df
                    
            if chart_type == AnalysisFilterPanel.CHART_PRICE:
                self.chart_engine.draw_price_chart(data_map)
            elif chart_type == AnalysisFilterPanel.CHART_RETURNS:
                self.chart_engine.draw_returns_chart(data_map)
            elif chart_type == AnalysisFilterPanel.CHART_COMPARISON:
                self.chart_engine.draw_comparison_chart(data_map)

    def _render_pie_chart(self, mode: str):
        portfolio = self.portfolio_service.get_current_portfolio()
        positions = [(p.stock_id, p.total_quantity, p.total_cost) for p in portfolio.positions.values() if p.total_quantity > 0]
        
        if not positions:
            self.chart_engine.draw_empty_chart("Portföyde pozisyon yok")
            return
            
        stock_ids = [p[0] for p in positions]
        ticker_map = self.stock_repo.get_ticker_map_for_stock_ids(stock_ids)
        
        breakdown = []
        for pos in positions:
            stock_id, qty, cost = pos
            ticker = ticker_map.get(stock_id, "?")
            
            if mode == "cost":
                breakdown.append((ticker, float(cost)))
            else:
                data = self._fetch_price_data(ticker, stock_id)
                if data is not None and not data.empty:
                    close_col = 'Close' if 'Close' in data.columns else data.columns[0]
                    if hasattr(data[close_col], 'values') and len(data[close_col].shape) > 1:
                        last_price = float(data[close_col].iloc[-1, 0])
                    else:
                        last_price = float(data[close_col].iloc[-1])
                    breakdown.append((ticker, last_price * float(qty)))
                else:
                    breakdown.append((f"{ticker}*", float(cost)))
                    
        title = "Portföy Dağılımı (Maliyet Bazlı)" if mode == "cost" else "Portföy Dağılımı (Güncel Değer)"
        self.chart_engine.draw_portfolio_pie(title, breakdown)

    def _on_save_chart(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Grafiği Kaydet", f"grafik_{date.today().strftime('%Y%m%d')}.png",
            "PNG Dosyası (*.png);;PDF Dosyası (*.pdf);;SVG Dosyası (*.svg)"
        )
        if file_path:
            try:
                self.chart_engine.save_chart(file_path)
                QMessageBox.information(self, "Başarılı", f"Grafik kaydedildi:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Kaydedilemedi:\n{e}")

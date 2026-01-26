# src/ui/main_window.py

from __future__ import annotations

import yfinance as yf
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, NamedTuple, Optional

from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFrame,
    QStackedWidget,
)
from PyQt5.QtCore import Qt


class PriceLookupResult(NamedTuple):
    price: Decimal
    as_of: datetime
    source: str


class MainWindow(QMainWindow):
    """
    Ana uygulama penceresi.
    QStackedWidget ile sayfa tabanlı navigasyon.
    """
    
    # Sayfa indeksleri
    PAGE_DASHBOARD = 0
    PAGE_WATCHLIST = 1
    PAGE_MODEL_PORTFOLIO = 2
    PAGE_ANALYSIS = 3

    def __init__(
        self,
        portfolio_service,
        return_calc_service,
        update_coordinator,
        excel_export_service,
        stock_repo,
        reset_service,
        market_client,
        watchlist_service=None,
        model_portfolio_service=None,
        parent=None,
    ):
        super().__init__(parent)
        self.portfolio_service = portfolio_service
        self.return_calc_service = return_calc_service
        self.update_coordinator = update_coordinator
        self.stock_repo = stock_repo
        self.reset_service = reset_service
        self.market_client = market_client
        self.excel_export_service = excel_export_service
        self.watchlist_service = watchlist_service
        self.model_portfolio_service = model_portfolio_service
        
        # Navigasyon geçmişi
        self.navigation_history: List[int] = []
        
        self.setWindowTitle("Portföy Simülasyonu")
        self.resize(1200, 700)

        self._init_ui()
        self._goto_page(self.PAGE_DASHBOARD)

    def _init_ui(self):
        # Ana Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Ana Layout (Yatay): Sol Menü | Sağ İçerik
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- 1. SOL MENÜ (SIDEBAR) ---
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(220)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(15, 25, 15, 25)
        self.sidebar_layout.setSpacing(10)

        # Logo/Başlık
        lbl_app_title = QLabel("📈 Portföy\nSimülasyonu")
        lbl_app_title.setStyleSheet("""
            font-size: 18px; 
            font-weight: bold; 
            color: #f1f5f9;
            padding: 10px 0;
        """)
        lbl_app_title.setAlignment(Qt.AlignCenter)
        self.sidebar_layout.addWidget(lbl_app_title)

        # Ayraç
        self._add_separator()

        self.btn_dashboard = self._create_nav_button("🏠 Dashboard", self.PAGE_DASHBOARD)
        self.btn_watchlist = self._create_nav_button("📋 Listelerim", self.PAGE_WATCHLIST)
        self.btn_model_portfolio = self._create_nav_button("📊 Model Portföyler", self.PAGE_MODEL_PORTFOLIO)
        self.btn_analysis = self._create_nav_button("📈 Analiz", self.PAGE_ANALYSIS)

        self.sidebar_layout.addWidget(self.btn_dashboard)
        self.sidebar_layout.addWidget(self.btn_watchlist)
        self.sidebar_layout.addWidget(self.btn_model_portfolio)
        self.sidebar_layout.addWidget(self.btn_analysis)

        self.sidebar_layout.addStretch()

        # Geri butonu
        self._add_separator()
        
        self.btn_back = QPushButton("← Geri")
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.clicked.connect(self._on_back)
        self.btn_back.setEnabled(False)
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                border: 1px solid #334155;
                padding: 10px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
            QPushButton:disabled {
                color: #475569;
                border-color: #1e293b;
            }
        """)
        self.sidebar_layout.addWidget(self.btn_back)

        # --- 2. SAĞ İÇERİK ALANI (STACKED WIDGET) ---
        self.stacked_widget = QStackedWidget()
        
        # Sayfaları oluştur ve ekle
        self._create_pages()

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.stacked_widget, 1)

    def _create_nav_button(self, text: str, page_index: int) -> QPushButton:
        """Navigasyon butonu oluşturur."""
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setCheckable(True)
        btn.clicked.connect(lambda: self._goto_page(page_index))
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #94a3b8;
                border: none;
                padding: 12px 15px;
                text-align: left;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1e293b;
                color: #f1f5f9;
            }
            QPushButton:checked {
                background-color: #3b82f6;
                color: white;
            }
        """)
        return btn

    def _add_separator(self):
        """Sidebar'a ayraç ekler."""
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #334155; margin: 10px 0;")
        self.sidebar_layout.addWidget(line)

    def _create_pages(self):
        """Sayfa widget'larını oluşturur."""
        from src.ui.pages.dashboard_page import DashboardPage
        from src.ui.pages.watchlist_page import WatchlistPage
        from src.ui.pages.model_portfolio_page import ModelPortfolioPage

        # Dashboard Page
        self.dashboard_page = DashboardPage(
            portfolio_service=self.portfolio_service,
            return_calc_service=self.return_calc_service,
            update_coordinator=self.update_coordinator,
            stock_repo=self.stock_repo,
            reset_service=self.reset_service,
            market_client=self.market_client,
            excel_export_service=self.excel_export_service,
            price_lookup_func=self.lookup_price_for_ticker,
        )
        self.stacked_widget.addWidget(self.dashboard_page)  # Index 0

        # Watchlist Page
        self.watchlist_page = WatchlistPage(
            watchlist_service=self.watchlist_service,
        )
        self.stacked_widget.addWidget(self.watchlist_page)  # Index 1

        self.model_portfolio_page = ModelPortfolioPage(
            model_portfolio_service=self.model_portfolio_service,
            price_lookup_func=self.lookup_price_for_ticker,
        )
        self.stacked_widget.addWidget(self.model_portfolio_page)  # Index 2

        # Analysis Page
        from src.ui.pages.analysis_page import AnalysisPage
        self.analysis_page = AnalysisPage(
            stock_repo=self.stock_repo,
            portfolio_service=self.portfolio_service,
            price_repo=None,  # Opsiyonel
        )
        self.stacked_widget.addWidget(self.analysis_page)  # Index 3

    def _goto_page(self, page_index: int):
        """Belirtilen sayfaya geçiş yapar."""
        current_index = self.stacked_widget.currentIndex()
        
        # Aynı sayfa değilse geçmişe ekle
        if current_index != page_index:
            self.navigation_history.append(current_index)
        
        # Sayfayı değiştir
        self.stacked_widget.setCurrentIndex(page_index)
        
        # Yeni sayfanın on_page_enter metodunu çağır
        current_page = self.stacked_widget.currentWidget()
        if hasattr(current_page, 'on_page_enter'):
            current_page.on_page_enter()
        
        # Buton durumlarını güncelle
        self._update_nav_buttons(page_index)
        
        # Geri butonunu güncelle
        self.btn_back.setEnabled(len(self.navigation_history) > 0)

    def _on_back(self):
        """Önceki sayfaya döner."""
        if not self.navigation_history:
            return
        
        previous_page = self.navigation_history.pop()
        self.stacked_widget.setCurrentIndex(previous_page)
        
        # Yeni sayfanın on_page_enter metodunu çağır
        current_page = self.stacked_widget.currentWidget()
        if hasattr(current_page, 'on_page_enter'):
            current_page.on_page_enter()
        
        # Buton durumlarını güncelle
        self._update_nav_buttons(previous_page)
        
        # Geri butonunu güncelle
        self.btn_back.setEnabled(len(self.navigation_history) > 0)

    def _update_nav_buttons(self, active_page: int):
        """Navigasyon butonlarının aktif durumunu günceller."""
        self.btn_dashboard.setChecked(active_page == self.PAGE_DASHBOARD)
        self.btn_watchlist.setChecked(active_page == self.PAGE_WATCHLIST)
        self.btn_model_portfolio.setChecked(active_page == self.PAGE_MODEL_PORTFOLIO)
        self.btn_analysis.setChecked(active_page == self.PAGE_ANALYSIS)

    def lookup_price_for_ticker(self, ticker: str) -> Optional[PriceLookupResult]:
        """Hisse fiyatını sorgular."""
        if not ticker:
            return None

        if "." not in ticker:
            ticker = ticker.upper() + ".IS"
        else:
            ticker = ticker.upper()

        try:
            yt = yf.Ticker(ticker)
        except Exception as e:
            print("YF Ticker init failed:", e)
            return None

        info = {}
        try:
            info = getattr(yt, "fast_info", None) or yt.info
        except Exception:
            info = {}

        if isinstance(info, dict):
            candidates = [
                info.get("lastPrice"),
                info.get("last_price"),
                info.get("regularMarketPrice"),
                info.get("currentPrice"),
            ]
            for v in candidates:
                if v is not None:
                    try:
                        price = Decimal(str(float(v)))
                        as_of = datetime.now(timezone.utc)
                        return PriceLookupResult(price=price, as_of=as_of, source="intraday")
                    except Exception:
                        pass

        try:
            hist = yt.history(period="5d", auto_adjust=False)
        except Exception as e:
            print("YF history failed for", ticker, ":", e)
            return None

        if hist is not None and not hist.empty and "Close" in hist:
            close_series = hist["Close"].dropna()
            if not close_series.empty:
                last_ts = close_series.index[-1]
                last_price = close_series.iloc[-1]
                try:
                    price = Decimal(str(float(last_price)))
                    if hasattr(last_ts, "to_pydatetime"):
                        as_of = last_ts.to_pydatetime().replace(tzinfo=timezone.utc)
                    else:
                        as_of = datetime.now(timezone.utc)
                    return PriceLookupResult(price=price, as_of=as_of, source="last_close")
                except Exception:
                    pass

        print("Price lookup failed for", ticker)
        return None
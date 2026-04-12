# src/ui/pages/dashboard/dashboard_page.py

import logging
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QDialog, QFileDialog
)
from PyQt5.QtCore import Qt, QModelIndex, QThreadPool

from src.ui.pages.base_page import BasePage
from src.ui.portfolio_table_model import PortfolioTableModel
from src.ui.worker import Worker
from src.ui.widgets.date_range_dialog import DateRangeDialog
from src.ui.widgets.new_stock_trade_dialog import NewStockTradeDialog
from src.ui.widgets.edit_stock_dialog import EditStockDialog
from src.ui.widgets.capital_dialog import CapitalDialog
from src.ui.widgets.backfill_dialog import BackfillDialog

from src.domain.models.stock import Stock
from src.domain.models.trade import Trade, TradeSide
from src.domain.models.position import Position
from src.domain.models.portfolio import Portfolio
from src.application.services.daily_history_models import ExportMode

from .dashboard_summary_cards import DashboardSummaryCards
from .dashboard_portfolio_table import DashboardPortfolioTable

logger = logging.getLogger(__name__)

class DashboardPage(BasePage):
    """
    Ana dashboard sayfası orchestrator'ı.
    Alt bileşenlerle arayüzü çizer, asıl iş mantığı ve sinyalleri yönetir.
    """

    def __init__(
        self,
        container,
        price_lookup_func,
        parent=None,
    ):
        super().__init__(parent)
        self.container = container
        self.page_title = "Dashboard"
        
        self.portfolio_service = container.portfolio_service
        self.return_calc_service = container.return_calc_service
        self.update_coordinator = container.update_coordinator
        self.stock_repo = container.stock_repo
        self.reset_service = container.reset_service
        self.market_client = container.market_client
        self.excel_export_service = container.excel_export_service
        self.price_lookup_func = price_lookup_func
        self.backfill_service = container.backfill_service
        
        self.threadpool = QThreadPool()
        self._capital = Decimal("0")
        
        self.portfolio_model = None
        self._is_refreshing = False
        
        self._init_ui()
        
        if self.container.event_bus:
            self.container.event_bus.prices_updated.connect(self._on_prices_updated_event)

    def _init_ui(self):
        # Üst Aksiyonlar
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)
        
        self.btn_new_trade = QPushButton("➕ Yeni İşlem")
        self.btn_new_trade.setObjectName("primaryButton")
        self.btn_new_trade.setCursor(Qt.PointingHandCursor)
        self.btn_new_trade.clicked.connect(self._on_new_trade)
        
        self.btn_update_prices = QPushButton("🔄 Fiyatları Güncelle")
        self.btn_update_prices.setCursor(Qt.PointingHandCursor)
        self.btn_update_prices.clicked.connect(self._on_update_prices)
        
        self.lbl_last_update = QLabel("")
        self.lbl_last_update.setStyleSheet("color: #64748b; font-size: 11px; margin-left: 5px;")
        
        self.btn_capital = QPushButton("💰 Sermaye Yönetimi")
        self.btn_capital.setCursor(Qt.PointingHandCursor)
        self.btn_capital.clicked.connect(self._on_capital_management)
        self.btn_capital.setStyleSheet("""
            QPushButton {
                background-color: #1e293b; color: #f1f5f9; border: 1px solid #334155;
                padding: 8px 16px; border-radius: 6px;
            }
            QPushButton:hover { background-color: #334155; }
        """)
        
        self.btn_backfill = QPushButton("📦 Geçmiş Veri Yönetimi")
        self.btn_backfill.setCursor(Qt.PointingHandCursor)
        self.btn_backfill.clicked.connect(self._on_backfill)
        self.btn_backfill.setStyleSheet(self.btn_capital.styleSheet())

        top_layout.addWidget(self.btn_new_trade)
        top_layout.addWidget(self.btn_update_prices)
        top_layout.addWidget(self.lbl_last_update)
        top_layout.addWidget(self.btn_capital)
        top_layout.addWidget(self.btn_backfill)
        top_layout.addStretch()
        
        self.main_layout.addLayout(top_layout)

        # Kartlar
        self.summary_cards = DashboardSummaryCards()
        self.main_layout.addWidget(self.summary_cards)

        # Tablo
        self.portfolio_table_widget = DashboardPortfolioTable()
        self.portfolio_table_widget.row_double_clicked.connect(self._on_table_double_clicked)
        self.main_layout.addWidget(self.portfolio_table_widget)

        # Alt Butonlar (Footer)
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        self.btn_export_today = QPushButton("📄 Rapor: Bugün")
        self.btn_export_today.setCursor(Qt.PointingHandCursor)
        self.btn_export_today.clicked.connect(self._on_export_today)
        
        self.btn_export_range = QPushButton("📄 Rapor: Tarih Aralığı")
        self.btn_export_range.setCursor(Qt.PointingHandCursor)
        self.btn_export_range.clicked.connect(self._on_export_range)
        
        self.btn_reset = QPushButton("🗑️ Sistemi Sıfırla")
        self.btn_reset.setStyleSheet("color: #ef4444;")
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.clicked.connect(self._on_reset)
        
        bottom_layout.addWidget(self.btn_export_today)
        bottom_layout.addWidget(self.btn_export_range)
        bottom_layout.addWidget(self.btn_reset)
        
        self.main_layout.addLayout(bottom_layout)

    def on_page_enter(self):
        """Sayfa aktif olduğunda verileri yükle."""
        self._load_capital()
        self.refresh_data()

    def _load_capital(self):
        try:
            self._capital = self.portfolio_service.calculate_capital()
        except Exception as e:
            logger.error(f"Sermaye yüklenemedi: {e}", exc_info=True)
            self._capital = Decimal("0")

    def refresh_data(self):
        portfolio: Portfolio = self.portfolio_service.get_current_portfolio()
        today = date.today()
        
        snapshot = self.return_calc_service.compute_portfolio_value_on(today)

        all_positions: List[Position] = list(portfolio.positions.values())
        positions: List[Position] = [p for p in all_positions if p.total_quantity != 0]

        price_map: Dict[int, Decimal] = snapshot.price_map if snapshot else {}

        stock_ids = [p.stock_id for p in positions]
        ticker_map = self.stock_repo.get_ticker_map_for_stock_ids(stock_ids)

        if self.portfolio_model is None:
            self.portfolio_model = PortfolioTableModel(
                positions, 
                price_map, 
                ticker_map, 
                event_bus=self.container.event_bus, 
                parent=self
            )
            self.portfolio_table_widget.set_model(self.portfolio_model)
        else:
            current_ids = set(p.stock_id for p in positions)
            model_ids = set(p.stock_id for p in self.portfolio_model._positions)
            
            if len(positions) != self.portfolio_model.rowCount() or current_ids != model_ids:
                self.portfolio_model.update_data(positions, price_map, ticker_map)

        total_value = snapshot.total_value if snapshot else Decimal("0")
        total_cost = sum(p.total_cost for p in positions)
        profit_loss = total_value - total_cost

        self.summary_cards.update_base_metrics(total_value, total_cost, self._capital, profit_loss)
        self.portfolio_table_widget.update_summary_row(total_value, profit_loss)

    def _on_prices_updated_event(self, new_prices: Dict[int, Decimal]):
        if not self.portfolio_model or getattr(self, "_is_refreshing", False):
            return
            
        price_map = getattr(self.portfolio_model, '_price_map', {})
        
        total_cost = Decimal("0")
        total_value = Decimal("0")
        
        for p in self.portfolio_model._positions:
            if p.total_quantity > 0:
                total_cost += p.total_cost
                curr_price = price_map.get(p.stock_id, Decimal("0"))
                total_value += p.market_value(curr_price)
                
        profit_loss = total_value - total_cost

        self.summary_cards.update_base_metrics(total_value, total_cost, self._capital, profit_loss)
        self.portfolio_table_widget.update_summary_row(total_value, profit_loss)

    def _on_capital_management(self):
        dialog = CapitalDialog(self._capital, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        
        result = dialog.get_result()
        if not result:
            return
        
        action = result["action"]
        amount = result["amount"]
        
        if action == "deposit":
            self._capital += amount
            QMessageBox.information(self, "Başarılı", f"₺{amount:,.2f} sermaye eklendi.")
        else:
            if amount > self._capital:
                QMessageBox.warning(self, "Uyarı", "Yetersiz sermaye.")
                return
            self._capital -= amount
            QMessageBox.information(self, "Başarılı", f"₺{amount:,.2f} sermaye çekildi.")
        
        self.refresh_data()

    def _on_new_trade(self):
        dlg = NewStockTradeDialog(
            parent=self, price_lookup_func=self.price_lookup_func, lot_size=1,
        )
        if dlg.exec_() != QDialog.Accepted:
            return

        data = dlg.get_result()
        if not data:
            return

        ticker = data["ticker"]
        name = data["name"]

        try:
            existing_stock = self.stock_repo.get_stock_by_ticker(ticker)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Hisse sorgulanırken hata: {e}")
            return

        if existing_stock is None:
            try:
                new_stock = Stock(id=None, ticker=ticker, name=name or ticker, currency_code="TRY")
                saved_stock = self.stock_repo.insert_stock(new_stock)
                stock_id = saved_stock.id
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Yeni hisse eklenemedi: {e}")
                return
        else:
            stock_id = existing_stock.id

        trade_amount = data["price"] * Decimal(data["quantity"])

        try:
            if data["side"] == "BUY":
                trade = Trade.create_buy(
                    stock_id=stock_id, trade_date=data["trade_date"],
                    trade_time=data["trade_time"], quantity=data["quantity"], price=data["price"],
                )
                self._capital -= trade_amount
                self._capital = max(Decimal("0"), self._capital)
            else:
                trade = Trade.create_sell(
                    stock_id=stock_id, trade_date=data["trade_date"],
                    trade_time=data["trade_time"], quantity=data["quantity"], price=data["price"],
                )
                self._capital += trade_amount
            
            self.portfolio_service.add_trade(trade)
            self.refresh_data()
            QMessageBox.information(self, "Başarılı", "İşlem başarıyla eklendi.")
        except ValueError as e:
            QMessageBox.warning(self, "Geçersiz İşlem", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"İşlem kaydedilemedi: {e}")

    def _on_update_prices(self):
        self.btn_update_prices.setEnabled(False)
        self.btn_update_prices.setText("🔄 Güncelleniyor...")
        self.btn_backfill.setEnabled(False)
        
        worker = Worker(self.update_coordinator.update_today_prices_and_get_snapshot)
        worker.signals.result.connect(self._on_update_prices_success)
        worker.signals.error.connect(self._on_update_prices_error)
        
        def on_finished():
            self.btn_update_prices.setEnabled(True)
            self.btn_update_prices.setText("🔄 Fiyatları Güncelle")
            self.btn_backfill.setEnabled(True)
            
        worker.signals.finished.connect(on_finished)
        self.threadpool.start(worker)

    def _on_update_prices_success(self, result):
        price_update_result, snapshot = result
        self.refresh_data()
        self._update_returns()
        
        from datetime import datetime
        now_str = datetime.now().strftime("%H:%M")
        self.lbl_last_update.setText(f"Son güncelleme: {now_str} (15dk gecikmeli)")
        
        QMessageBox.information(self, "Güncelleme Tamamlandı", f"{price_update_result.updated_count} hisse güncellendi.")

    def _on_update_prices_error(self, err_tuple):
        exctype, value, tb_str = err_tuple
        QMessageBox.critical(self, "Hata", f"Hata:\n{value}")

    def _update_returns(self):
        today = date.today()
        try:
            weekly_rate, _, _ = self.return_calc_service.compute_weekly_return(today)
            monthly_rate, _, _ = self.return_calc_service.compute_monthly_return(today)
        except Exception as e:
            logger.error(f"Getiri hesaplama hatası: {e}", exc_info=True)
            return

        w_pct = float(weekly_rate)*100 if weekly_rate is not None else None
        m_pct = float(monthly_rate)*100 if monthly_rate is not None else None
        self.summary_cards.update_returns(w_pct, m_pct)

    def _on_table_double_clicked(self, index: QModelIndex):
        if not index.isValid() or self.portfolio_model is None:
            return

        row = index.row()
        if row < 0 or row >= self.portfolio_model.rowCount():
            return

        position: Position = self.portfolio_model.get_position(row)
        stock_id = position.stock_id
        stock = self.stock_repo.get_stock_by_id(stock_id)
        ticker = stock.ticker if stock else None

        main_window = self.window()
        if hasattr(main_window, "show_stock_detail"):
            main_window.show_stock_detail(ticker, stock_id)
        else:
            QMessageBox.warning(self, "Hata", "Detay sayfasına erişilemedi.")

    def _get_first_trade_date(self):
        return self.portfolio_service.get_first_trade_date()

    def _on_export_today(self):
        first_date = self._get_first_trade_date()
        if first_date is None:
            QMessageBox.information(self, "Bilgi", "Herhangi bir işlem bulunamadı.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Excel Dosyası Seç", "portfoy_takip.xlsx", "Excel Dosyaları (*.xlsx)")
        if not file_path:
            return

        try:
            self.excel_export_service.export_history(start_date=first_date, end_date=date.today(), file_path=file_path, mode=ExportMode.OVERWRITE)
            QMessageBox.information(self, "Başarılı", "Excel aktarımı tamamlandı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Excel hatası: {e}")

    def _on_export_range(self):
        first_date = self._get_first_trade_date()
        if first_date is None:
            QMessageBox.information(self, "Bilgi", "İşlem bulunamadı.")
            return

        dlg = DateRangeDialog(self, min_date=first_date, max_date=date.today())
        if dlg.exec_() != QDialog.Accepted:
            return

        result = dlg.get_range()
        if not result:
            return
        start_date, end_date = result

        file_path, _ = QFileDialog.getSaveFileName(self, "Excel Seç", "portfoy_takip.xlsx", "Excel Dosyaları (*.xlsx)")
        if not file_path: return

        try:
            self.excel_export_service.export_history(start_date=start_date, end_date=end_date, file_path=file_path, mode=ExportMode.OVERWRITE)
            QMessageBox.information(self, "Başarılı", "Excel aktarımı tamamlandı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Hata: {e}")

    def _on_reset(self):
        reply = QMessageBox.question(
            self, "Portföyü Sıfırla", "TÜM veriler silinecek. Emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes: return
        try:
            self.reset_service.reset_all()
            self._capital = Decimal("0")
            self.refresh_data()
            self.summary_cards.update_returns(None, None)
            QMessageBox.information(self, "Tamamlandı", "Başarıyla sıfırlandı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Hata: {e}")

    def _on_backfill(self):
        if not self.backfill_service:
            QMessageBox.warning(self, "Uyarı", "Backfill servisi kullanılamıyor.")
            return

        dialog = BackfillDialog(self)
        if dialog.exec_() != QDialog.Accepted: return
        result = dialog.get_result()
        if not result:
            QMessageBox.warning(self, "Uyarı", "Başlangıç bitişten sonra olamaz.")
            return

        action, start_date, end_date = result["action"], result["start_date"], result["end_date"]

        if action == "delete":
            reply = QMessageBox.question(self, "Silme Onayı", "Veriler silinecek, emin misiniz?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes: return
            try:
                count = self.backfill_service.delete_range(start_date, end_date)
                self.refresh_data()
                QMessageBox.information(self, "Başarılı", f"{count} veri silindi.")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Hata: {e}")
        else:
            self.btn_backfill.setEnabled(False)
            self.btn_backfill.setText("⏳ İndiriliyor...")
            self.btn_update_prices.setEnabled(False)

            worker = Worker(self.backfill_service.backfill_range, start_date, end_date)
            worker.signals.result.connect(lambda count, sd=start_date, ed=end_date: self._on_backfill_success(count, sd, ed))
            worker.signals.error.connect(self._on_backfill_error)
            
            def on_finished():
                self.btn_backfill.setEnabled(True)
                self.btn_backfill.setText("📦 Geçmiş Veri Yönetimi")
                self.btn_update_prices.setEnabled(True)
                
            worker.signals.finished.connect(on_finished)
            self.threadpool.start(worker)

    def _on_backfill_success(self, count, start_date, end_date):
        self.refresh_data()
        QMessageBox.information(self, "Başarılı", f"{count} veri indirildi.")

    def _on_backfill_error(self, err_tuple):
        QMessageBox.critical(self, "Hata", f"Hata:\n{err_tuple[1]}")

# src/ui/pages/dashboard_page.py

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, NamedTuple

from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTableView,
    QMessageBox,
    QFrame,
    QHeaderView,
    QDialog,
    QFileDialog,
)
from PyQt5.QtCore import Qt, QModelIndex

from .base_page import BasePage
from src.ui.portfolio_table_model import PortfolioTableModel
from src.ui.widgets.date_range_dialog import DateRangeDialog
from src.ui.widgets.trade_dialog import TradeDialog
from src.ui.widgets.new_stock_trade_dialog import NewStockTradeDialog
from src.ui.widgets.edit_stock_dialog import EditStockDialog

from src.domain.models.stock import Stock
from src.domain.models.trade import Trade, TradeSide
from src.domain.models.position import Position
from src.domain.models.portfolio import Portfolio
from src.application.services.excel_export_service import ExportMode


class DashboardPage(BasePage):
    """
    Ana dashboard sayfası.
    Portföy özeti, hisse tablosu ve işlem ekleme.
    """

    def __init__(
        self,
        portfolio_service,
        return_calc_service,
        update_coordinator,
        stock_repo,
        reset_service,
        market_client,
        excel_export_service,
        price_lookup_func,
        parent=None,
    ):
        super().__init__(parent)
        self.page_title = "Dashboard"
        
        self.portfolio_service = portfolio_service
        self.return_calc_service = return_calc_service
        self.update_coordinator = update_coordinator
        self.stock_repo = stock_repo
        self.reset_service = reset_service
        self.market_client = market_client
        self.excel_export_service = excel_export_service
        self.price_lookup_func = price_lookup_func
        
        self.model = None
        self._init_ui()

    def _init_ui(self):
        # Üst aksiyon butonları
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        
        self.btn_new_trade = QPushButton("➕ Yeni İşlem")
        self.btn_new_trade.setObjectName("primaryButton")
        self.btn_new_trade.setCursor(Qt.PointingHandCursor)
        self.btn_new_trade.clicked.connect(self._on_new_trade)
        
        self.btn_update_prices = QPushButton("🔄 Fiyatları Güncelle")
        self.btn_update_prices.setCursor(Qt.PointingHandCursor)
        self.btn_update_prices.clicked.connect(self._on_update_prices)
        
        self.btn_refresh_returns = QPushButton("📊 Getiri Analizi")
        self.btn_refresh_returns.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_returns.clicked.connect(self._on_refresh_returns)
        
        action_layout.addWidget(self.btn_new_trade)
        action_layout.addWidget(self.btn_update_prices)
        action_layout.addWidget(self.btn_refresh_returns)
        action_layout.addStretch()
        
        self.main_layout.addLayout(action_layout)

        # Dashboard Kartları
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)

        self.card_total, self.lbl_total_value = self._create_card("TOPLAM PORTFÖY DEĞERİ", "₺ 0.00")
        self.card_weekly, self.lbl_weekly_return = self._create_card("HAFTALIK GETİRİ", "-")
        self.card_monthly, self.lbl_monthly_return = self._create_card("AYLIK GETİRİ", "-")

        cards_layout.addWidget(self.card_total)
        cards_layout.addWidget(self.card_weekly)
        cards_layout.addWidget(self.card_monthly)

        self.main_layout.addLayout(cards_layout)

        # Tablo
        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(False)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setSortingEnabled(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.setShowGrid(False)
        self.table_view.doubleClicked.connect(self._on_table_double_clicked)

        self.main_layout.addWidget(self.table_view)

        # Alt butonlar (Rapor)
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

    def _create_card(self, title, initial_value):
        """Dashboard kartı oluşturur."""
        card = QFrame()
        card.setObjectName("infoCard")
        card.setFrameShape(QFrame.StyledPanel)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        
        lbl_title = QLabel(title)
        lbl_title.setObjectName("cardTitle")
        
        lbl_value = QLabel(initial_value)
        lbl_value.setObjectName("cardValue")
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        return card, lbl_value

    def on_page_enter(self):
        """Sayfa aktif olduğunda verileri yükle."""
        self.refresh_data()

    def refresh_data(self):
        """Portföy verilerini yenile."""
        portfolio: Portfolio = self.portfolio_service.get_current_portfolio()
        today = date.today()
        
        snapshot = self.return_calc_service.compute_portfolio_value_on(today)

        all_positions: List[Position] = list(portfolio.positions.values())
        positions: List[Position] = [p for p in all_positions if p.total_quantity != 0]

        price_map: Dict[int, Decimal] = snapshot.price_map if snapshot else {}

        stock_ids = [p.stock_id for p in positions]
        ticker_map = self.stock_repo.get_ticker_map_for_stock_ids(stock_ids)

        if self.model is None:
            self.model = PortfolioTableModel(positions, price_map, ticker_map, parent=self)
            self.table_view.setModel(self.model)
        else:
            self.model.update_data(positions, price_map, ticker_map)

        if snapshot:
            self.lbl_total_value.setText(f"₺ {snapshot.total_value:,.2f}")

    def _on_new_trade(self):
        """Yeni işlem ekleme diyaloğu."""
        dlg = NewStockTradeDialog(
            parent=self,
            price_lookup_func=self.price_lookup_func,
            lot_size=1,
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

        try:
            if data["side"] == "BUY":
                trade = Trade.create_buy(
                    stock_id=stock_id,
                    trade_date=data["trade_date"],
                    trade_time=data["trade_time"],
                    quantity=data["quantity"],
                    price=data["price"],
                )
            else:
                trade = Trade.create_sell(
                    stock_id=stock_id,
                    trade_date=data["trade_date"],
                    trade_time=data["trade_time"],
                    quantity=data["quantity"],
                    price=data["price"],
                )
            self.portfolio_service.add_trade(trade)
            self.refresh_data()
            QMessageBox.information(self, "Başarılı", "İşlem başarıyla eklendi.")
        except ValueError as e:
            QMessageBox.warning(self, "Geçersiz İşlem", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"İşlem kaydedilemedi: {e}")

    def _on_update_prices(self):
        """Fiyatları güncelle."""
        try:
            price_update_result, snapshot = self.update_coordinator.update_today_prices_and_get_snapshot()
            self.refresh_data()
            QMessageBox.information(
                self,
                "Güncelleme Tamamlandı",
                f"{price_update_result.updated_count} hisse için fiyat güncellendi.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Fiyat güncelleme sırasında hata: {e}")

    def _on_refresh_returns(self):
        """Getiri hesapla."""
        today = date.today()
        try:
            weekly_rate, _, _ = self.return_calc_service.compute_weekly_return(today)
            monthly_rate, _, _ = self.return_calc_service.compute_monthly_return(today)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Getiri hesaplama sırasında hata: {e}")
            return

        if weekly_rate is not None:
            self.lbl_weekly_return.setText(f"%{(weekly_rate * 100):.2f}")
        else:
            self.lbl_weekly_return.setText("-")

        if monthly_rate is not None:
            self.lbl_monthly_return.setText(f"%{(monthly_rate * 100):.2f}")
        else:
            self.lbl_monthly_return.setText("-")

    def _on_table_double_clicked(self, index: QModelIndex):
        """Tablo çift tıklama - işlem ekleme."""
        if not index.isValid() or self.model is None:
            return

        row = index.row()
        if row < 0 or row >= self.model.rowCount():
            return

        position: Position = self.model.get_position(row)
        stock_id = position.stock_id
        stock = self.stock_repo.get_stock_by_id(stock_id)
        ticker = stock.ticker if stock else None

        dialog = TradeDialog(
            stock_id=stock_id,
            ticker=ticker,
            parent=self,
            price_lookup_func=self.price_lookup_func,
            lot_size=1,
        )

        if dialog.exec_() != QDialog.Accepted:
            return

        if dialog.get_mode() == "edit_stock":
            if stock is None:
                QMessageBox.warning(self, "Uyarı", "Bu pozisyona ait hisse kaydı bulunamadı.")
                return
            self._edit_stock(stock)
            return

        trade_data = dialog.get_trade_data()
        if not trade_data:
            return

        try:
            if trade_data["side"] == "BUY":
                trade = Trade.create_buy(
                    stock_id=trade_data["stock_id"],
                    trade_date=trade_data["trade_date"],
                    trade_time=trade_data["trade_time"],
                    quantity=trade_data["quantity"],
                    price=trade_data["price"],
                )
            else:
                trade = Trade.create_sell(
                    stock_id=trade_data["stock_id"],
                    trade_date=trade_data["trade_date"],
                    trade_time=trade_data["trade_time"],
                    quantity=trade_data["quantity"],
                    price=trade_data["price"],
                )
            self.portfolio_service.add_trade(trade)
            self.refresh_data()
        except ValueError as e:
            QMessageBox.warning(self, "Geçersiz İşlem", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"İşlem kaydedilemedi: {e}")

    def _edit_stock(self, stock: Stock):
        """Hisse düzenleme."""
        edit_dlg = EditStockDialog(stock, parent=self)
        if edit_dlg.exec_() != QDialog.Accepted:
            return

        try:
            result = edit_dlg.get_result()
            updated_stock = Stock(
                id=stock.id,
                ticker=result.ticker,
                name=result.name,
                currency_code=stock.currency_code,
                created_at=stock.created_at,
                updated_at=stock.updated_at,
            )
            self.stock_repo.update_stock(updated_stock)
            self.refresh_data()
            QMessageBox.information(self, "Başarılı", "Hisse bilgileri güncellendi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Hisse güncellenemedi: {e}")

    def _on_export_today(self):
        """Bugünün raporunu dışa aktar."""
        first_date = self._get_first_trade_date()
        if first_date is None:
            QMessageBox.information(self, "Bilgi", "Herhangi bir işlem bulunamadı.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Excel Dosyası Seç", "portfoy_takip.xlsx", "Excel Dosyaları (*.xlsx)"
        )
        if not file_path:
            return

        mode = ExportMode.OVERWRITE
        try:
            self.excel_export_service.export_history(
                start_date=first_date,
                end_date=date.today(),
                file_path=file_path,
                mode=mode,
            )
            QMessageBox.information(self, "Başarılı", "Excel aktarımı tamamlandı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Excel aktarımı sırasında hata: {e}")

    def _on_export_range(self):
        """Tarih aralığı raporu."""
        first_date = self._get_first_trade_date()
        if first_date is None:
            QMessageBox.information(self, "Bilgi", "Herhangi bir işlem bulunamadı.")
            return

        dlg = DateRangeDialog(self, min_date=first_date, max_date=date.today())
        if dlg.exec_() != QDialog.Accepted:
            return

        result = dlg.get_range()
        if not result:
            return
        start_date, end_date = result

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Excel Dosyası Seç", "portfoy_takip.xlsx", "Excel Dosyaları (*.xlsx)"
        )
        if not file_path:
            return

        try:
            self.excel_export_service.export_history(
                start_date=start_date,
                end_date=end_date,
                file_path=file_path,
                mode=ExportMode.OVERWRITE,
            )
            QMessageBox.information(self, "Başarılı", "Excel aktarımı tamamlandı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Excel aktarımı sırasında hata: {e}")

    def _on_reset(self):
        """Sistemi sıfırla."""
        reply = QMessageBox.question(
            self,
            "Portföyü Sıfırla",
            "TÜM hisse, işlem ve fiyat kayıtları silinecek.\nBu işlem geri alınamaz. Emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        try:
            self.reset_service.reset_all()
            self.refresh_data()
            self.lbl_total_value.setText("₺ 0.00")
            self.lbl_weekly_return.setText("-")
            self.lbl_monthly_return.setText("-")
            QMessageBox.information(self, "Tamamlandı", "Portföy başarıyla sıfırlandı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Portföy sıfırlanırken hata: {e}")

    def _get_first_trade_date(self):
        trades = self.portfolio_service._portfolio_repo.get_all_trades()
        if not trades:
            return None
        return min(t.trade_date for t in trades)

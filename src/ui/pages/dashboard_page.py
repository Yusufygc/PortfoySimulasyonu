# src/ui/pages/dashboard_page.py

from __future__ import annotations

import logging
from datetime import date

logger = logging.getLogger(__name__)
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
    QInputDialog,
    QFormLayout,
    QDoubleSpinBox,
    QComboBox,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
)
from PyQt5.QtCore import Qt, QModelIndex, QThreadPool
from PyQt5.QtGui import QPainter, QColor

from .base_page import BasePage
from src.ui.portfolio_table_model import PortfolioTableModel
from src.ui.worker import Worker
from src.ui.widgets.date_range_dialog import DateRangeDialog
from src.ui.widgets.trade_dialog import TradeDialog
from src.ui.widgets.new_stock_trade_dialog import NewStockTradeDialog
from src.ui.widgets.edit_stock_dialog import EditStockDialog

from src.domain.models.stock import Stock
from src.domain.models.trade import Trade, TradeSide
from src.domain.models.position import Position
from src.domain.models.portfolio import Portfolio
from src.application.services.daily_history_models import ExportMode
from src.ui.widgets.backfill_dialog import BackfillDialog


class DashboardPage(BasePage):
    """
    Ana dashboard sayfası.
    Portföy özeti, sermaye yönetimi, hisse tablosu ve işlem ekleme.
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
        
        # Sermaye takibi (başlangıçta 0, hisse alım/satımıyla değişir)
        self._capital = Decimal("0")
        
        self.model = None
        self._is_refreshing = False
        self._init_ui()
        
        if self.container.event_bus:
            self.container.event_bus.prices_updated.connect(self._on_prices_updated_event)

    def _on_prices_updated_event(self, new_prices: Dict[int, Decimal]):
        """EventBus'tan tetiklenir: Tablodaki fiyata göre Dashboard özet kartlarını asenkron canlandırır."""
        if not self.model or getattr(self, "_is_refreshing", False):
            return
            
        # self.model zaten _price_map'i içinde barındırıyor (ve güncelledi)
        price_map = getattr(self.model, '_price_map', {})
        
        total_cost = Decimal("0")
        total_value = Decimal("0")
        
        for p in self.model._positions:
            if p.total_quantity > 0:
                total_cost += p.total_cost
                curr_price = price_map.get(p.stock_id, Decimal("0"))
                total_value += p.market_value(curr_price)
                
        profit_loss = total_value - total_cost

        # Değerleri formatlayıp yaz
        self.lbl_total_value.setText(f"₺ {total_value:,.2f}")
        
        roi = 0
        if total_cost != 0:
            roi = (profit_loss / total_cost) * 100
            
        prefix = "▲" if profit_loss >= 0 else "▼"
        sign = "+" if profit_loss >= 0 else ""
        color = "#10b981" if profit_loss >= 0 else "#ef4444"
        
        self.lbl_total_context.setText(f"{prefix} ₺ {abs(profit_loss):,.2f} ({sign}{roi:.1f}% All Time)")
        self.lbl_total_context.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 500;")

        self._update_summary_row(total_value, profit_loss)

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
        
        self.lbl_last_update = QLabel("")
        self.lbl_last_update.setStyleSheet("color: #64748b; font-size: 11px; margin-left: 5px;")
        
        self.btn_capital = QPushButton("💰 Sermaye Yönetimi")
        self.btn_capital.setCursor(Qt.PointingHandCursor)
        self.btn_capital.clicked.connect(self._on_capital_management)
        self.btn_capital.setStyleSheet("""
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
        
        self.btn_backfill = QPushButton("📦 Geçmiş Veri Yönetimi")
        self.btn_backfill.setCursor(Qt.PointingHandCursor)
        self.btn_backfill.clicked.connect(self._on_backfill)
        self.btn_backfill.setStyleSheet("""
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

        action_layout.addWidget(self.btn_new_trade)
        action_layout.addWidget(self.btn_update_prices)
        action_layout.addWidget(self.lbl_last_update)
        action_layout.addWidget(self.btn_capital)
        action_layout.addWidget(self.btn_backfill)
        action_layout.addStretch()
        
        self.main_layout.addLayout(action_layout)

        # Dashboard Kartları - 2 satır
        # İlk satır: Değer ve Maliyet
        cards_row1 = QHBoxLayout()
        cards_row1.setSpacing(20)

        self.card_total, self.lbl_total_value, self.lbl_total_context = self._create_card("TOPLAM PORTFÖY DEĞERİ", "₺ 0.00", "#3b82f6")
        self.card_cost, self.lbl_total_cost, _ = self._create_card("TOPLAM MALİYET", "₺ 0.00", "#8b5cf6")
        self.card_capital, self.lbl_capital, _ = self._create_card("NAKİT SERMAYE", "₺ 0.00", "#10b981")
        
        # Kar/Zarar yerine Haftalık ve Aylık Getiri Kombine Kartı
        self.card_returns, self.lbl_weekly_return, self.lbl_monthly_return = self._create_returns_card()

        cards_row1.addWidget(self.card_total, 1)
        cards_row1.addWidget(self.card_cost, 1)
        cards_row1.addWidget(self.card_capital, 1)
        cards_row1.addWidget(self.card_returns, 1)

        self.main_layout.addLayout(cards_row1)

        # Tablo
        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(False)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setSortingEnabled(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.verticalHeader().setDefaultSectionSize(40) # Satır yüksekliği artırıldı
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.setShowGrid(False)
        self.table_view.doubleClicked.connect(self._on_table_double_clicked)
        
        self.row_delegate = PortfolioRowDelegate(self.table_view)
        self.table_view.setItemDelegate(self.row_delegate)

        self.main_layout.addWidget(self.table_view)

        # TOPLAM Özet Satırı (Tek satırlık QTableWidget)
        self.table_summary = QTableWidget(1, 7)
        self.table_summary.horizontalHeader().setVisible(False)
        self.table_summary.verticalHeader().setVisible(False)
        self.table_summary.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_summary.setFixedHeight(40) # Tek satır boyutu
        self.table_summary.setSelectionMode(QTableView.NoSelection)
        self.table_summary.setFocusPolicy(Qt.NoFocus)
        self.table_summary.setEditTriggers(QTableView.NoEditTriggers)
        self.table_summary.setShowGrid(False)
        self.table_summary.setStyleSheet("""
            QTableWidget {
                background-color: #1e293b;
                border-top: 2px solid #334155;
                font-weight: bold;
                color: #f1f5f9;
            }
        """)
        self.main_layout.addWidget(self.table_summary)

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

    def _create_card(self, title, initial_value, accent_color="#3b82f6"):
        """Dashboard kartı oluşturur."""
        card = QFrame()
        card.setObjectName("infoCard")
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(f"""
            QFrame#infoCard {{
                background-color: #1e293b;
                border-radius: 12px;
                border-left: 4px solid {accent_color};
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 15)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        
        lbl_value = QLabel(initial_value)
        lbl_value.setStyleSheet("color: #f1f5f9; font-size: 18px; font-weight: bold;")
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        
        # Context Label (Alt açıklama)
        lbl_context = QLabel("")
        lbl_context.setStyleSheet("color: #64748b; font-size: 11px; margin-top: 2px;")
        layout.addWidget(lbl_context)
        
        return card, lbl_value, lbl_context

    def _create_returns_card(self):
        """Haftalık ve aylık getiriyi beraber gösteren yeni kart."""
        card = QFrame()
        card.setObjectName("infoCard")
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet("""
            QFrame#infoCard {
                background-color: #1e293b;
                border-radius: 12px;
                border-left: 4px solid #f59e0b;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 15)
        
        lbl_title = QLabel("DÖNEMSEL GETİRİLER")
        lbl_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        layout.addWidget(lbl_title)
        
        returns_layout = QVBoxLayout()
        returns_layout.setSpacing(5)
        
        weekly_layout = QHBoxLayout()
        lbl_wk_title = QLabel("Haftalık:")
        lbl_wk_title.setStyleSheet("color: #94a3b8; font-size: 13px;")
        lbl_wk_value = QLabel("-")
        lbl_wk_value.setStyleSheet("color: #f1f5f9; font-size: 14px; font-weight: bold;")
        weekly_layout.addWidget(lbl_wk_title)
        weekly_layout.addWidget(lbl_wk_value)
        weekly_layout.addStretch()
        
        monthly_layout = QHBoxLayout()
        lbl_mo_title = QLabel("Aylık:")
        lbl_mo_title.setStyleSheet("color: #94a3b8; font-size: 13px;")
        lbl_mo_value = QLabel("-")
        lbl_mo_value.setStyleSheet("color: #f1f5f9; font-size: 14px; font-weight: bold;")
        monthly_layout.addWidget(lbl_mo_title)
        monthly_layout.addWidget(lbl_mo_value)
        monthly_layout.addStretch()
        
        returns_layout.addLayout(weekly_layout)
        returns_layout.addLayout(monthly_layout)
        
        layout.addLayout(returns_layout)
        
        return card, lbl_wk_value, lbl_mo_value

    def on_page_enter(self):
        """Sayfa aktif olduğunda verileri yükle."""
        self._load_capital()
        self.refresh_data()

    def _load_capital(self):
        """Sermayeyi veritabanından yükle (Service katmanından çekilir)."""
        try:
            self._capital = self.portfolio_service.calculate_capital()
        except Exception as e:
            logger.error(f"Sermaye yüklenemedi: {e}", exc_info=True)
            self._capital = Decimal("0")

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
            self.model = PortfolioTableModel(
                positions, 
                price_map, 
                ticker_map, 
                event_bus=self.container.event_bus, 
                parent=self
            )
            self.table_view.setModel(self.model)
        else:
            # EventBus sayesinde fiyat güncellemeleri asenkron / reaktif hücre bazlı olmuştur.
            # Tablo modelini baştan aşağı resetlememek (dondurmamak) için, 
            # sadece eklendi/çıkarıldı varsa (len or stock ids differs) hard reset yapıyoruz.
            current_ids = set(p.stock_id for p in positions)
            model_ids = set(p.stock_id for p in self.model._positions)
            
            if len(positions) != self.model.rowCount() or current_ids != model_ids:
                self.model.update_data(positions, price_map, ticker_map)

        # Değerleri hesapla
        total_value = snapshot.total_value if snapshot else Decimal("0")
        total_cost = sum(p.total_cost for p in positions)
        profit_loss = total_value - total_cost

        # Kartları güncelle
        self.lbl_total_value.setText(f"₺ {total_value:,.2f}")
        self.lbl_total_cost.setText(f"₺ {total_cost:,.2f}")
        self.lbl_capital.setText(f"₺ {self._capital:,.2f}")

        # Hero Metric Context (Total Value altına P/L)
        cost_basis = total_value - profit_loss
        roi = 0
        if cost_basis != 0:
            roi = (profit_loss / cost_basis) * 100
            
        prefix = "▲" if profit_loss >= 0 else "▼"
        sign = "+" if profit_loss >= 0 else ""
        color = "#10b981" if profit_loss >= 0 else "#ef4444"
        
        self.lbl_total_context.setText(f"{prefix} ₺ {abs(profit_loss):,.2f} ({sign}{roi:.1f}% All Time)")
        self.lbl_total_context.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 500;")

        self._update_summary_row(total_value, profit_loss)


    def _update_summary_row(self, total_value: Decimal, profit_loss: Decimal):
        """Alt kısımdaki toplam özet satırını günceller."""
        for col in range(7):
            item = QTableWidgetItem("")
            item.setTextAlignment(Qt.AlignCenter)
            self.table_summary.setItem(0, col, item)
            
        item_title = QTableWidgetItem("TOPLAM")
        item_title.setTextAlignment(Qt.AlignCenter)
        self.table_summary.setItem(0, 0, item_title)
        
        # Piyasa Değeri (Kolon 5)
        item_mv = QTableWidgetItem(f"{total_value:,.2f}")
        item_mv.setTextAlignment(Qt.AlignCenter)
        self.table_summary.setItem(0, 5, item_mv)
        
        # Kar/Zarar (Kolon 6)
        item_pl = QTableWidgetItem(f"{profit_loss:+,.2f}")
        item_pl.setTextAlignment(Qt.AlignCenter)
        
        if profit_loss > 0:
            item_pl.setForeground(QColor("#22c55e"))
        elif profit_loss < 0:
            item_pl.setForeground(QColor("#ef4444"))
        else:
            item_pl.setForeground(QColor("#f1f5f9"))
            
        self.table_summary.setItem(0, 6, item_pl)


    def _on_capital_management(self):
        """Sermaye yönetimi diyaloğu."""
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

        trade_amount = data["price"] * Decimal(data["quantity"])

        try:
            if data["side"] == "BUY":
                trade = Trade.create_buy(
                    stock_id=stock_id,
                    trade_date=data["trade_date"],
                    trade_time=data["trade_time"],
                    quantity=data["quantity"],
                    price=data["price"],
                )
                self._capital -= trade_amount
                self._capital = max(Decimal("0"), self._capital)
            else:
                trade = Trade.create_sell(
                    stock_id=stock_id,
                    trade_date=data["trade_date"],
                    trade_time=data["trade_time"],
                    quantity=data["quantity"],
                    price=data["price"],
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
        """Fiyatları asenkron güncelle ve getirileri hesapla."""
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
        
        QMessageBox.information(
            self,
            "Güncelleme Tamamlandı",
            f"{price_update_result.updated_count} hisse için fiyat güncellendi.",
        )

    def _on_update_prices_error(self, err_tuple):
        exctype, value, tb_str = err_tuple
        QMessageBox.critical(self, "Hata", f"Fiyat güncelleme sırasında hata:\n{value}")

    def _update_returns(self):
        """Haftalık ve aylık getirileri hesapla."""
        today = date.today()
        try:
            weekly_rate, _, _ = self.return_calc_service.compute_weekly_return(today)
            monthly_rate, _, _ = self.return_calc_service.compute_monthly_return(today)
        except Exception as e:
            logger.error(f"Getiri hesaplama hatası: {e}", exc_info=True)
            return

        if weekly_rate is not None:
            pct = weekly_rate * 100
            color = "#10b981" if pct >= 0 else "#ef4444"
            self.lbl_weekly_return.setText(f"%{pct:+.2f}")
            self.lbl_weekly_return.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
        else:
            self.lbl_weekly_return.setText("-")
            self.lbl_weekly_return.setStyleSheet("color: #f1f5f9; font-size: 14px; font-weight: bold;")

        if monthly_rate is not None:
            pct = monthly_rate * 100
            color = "#10b981" if pct >= 0 else "#ef4444"
            self.lbl_monthly_return.setText(f"%{pct:+.2f}")
            self.lbl_monthly_return.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
        else:
            self.lbl_monthly_return.setText("-")
            self.lbl_monthly_return.setStyleSheet("color: #f1f5f9; font-size: 14px; font-weight: bold;")

    def _on_table_double_clicked(self, index: QModelIndex):
        """Tablo çift tıklama - detay sayfası."""
        if not index.isValid() or self.model is None:
            return

        row = index.row()
        if row < 0 or row >= self.model.rowCount():
            return

        position: Position = self.model.get_position(row)
        stock_id = position.stock_id
        stock = self.stock_repo.get_stock_by_id(stock_id)
        ticker = stock.ticker if stock else None

        # MainWindow'a ulaş ve detay sayfasını aç
        main_window = self.window()
        if hasattr(main_window, "show_stock_detail"):
            main_window.show_stock_detail(ticker, stock_id)
        else:
            QMessageBox.warning(self, "Hata", "Detay sayfasına erişilemedi.")

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
            self._capital = Decimal("0")
            self.refresh_data()
            self.lbl_total_value.setText("₺ 0.00")
            self.lbl_total_cost.setText("₺ 0.00")
            self.lbl_capital.setText("₺ 0.00")
            self.lbl_weekly_return.setText("-")
            self.lbl_monthly_return.setText("-")
            QMessageBox.information(self, "Tamamlandı", "Portföy başarıyla sıfırlandı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Portföy sıfırlanırken hata: {e}")

    def _get_first_trade_date(self):
        return self.portfolio_service.get_first_trade_date()

    def _on_backfill(self):
        """Geçmişe yönelik veri yönetimi diyaloğu."""
        if not self.backfill_service:
            QMessageBox.warning(self, "Uyarı", "Backfill servisi kullanılamıyor.")
            return

        dialog = BackfillDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return

        result = dialog.get_result()
        if not result:
            QMessageBox.warning(self, "Uyarı", "Başlangıç tarihi bitiş tarihinden sonra olamaz.")
            return

        action = result["action"]
        start_date = result["start_date"]
        end_date = result["end_date"]

        if action == "delete":
            reply = QMessageBox.question(
                self, "Veri Silme Onayı",
                f"{start_date} — {end_date} arasındaki tüm fiyat verileri silinecek.\n"
                "Bu işlem geri alınamaz. Emin misiniz?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

            try:
                count = self.backfill_service.delete_range(start_date, end_date)
                self.refresh_data()
                QMessageBox.information(
                    self, "Başarılı", f"{count} adet fiyat verisi silindi."
                )
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Silme sırasında hata: {e}")
        else:
            # Veri çekme (Asenkron)
            self.btn_backfill.setEnabled(False)
            self.btn_backfill.setText("⏳ Veri indiriliyor...")
            self.btn_update_prices.setEnabled(False)

            worker = Worker(self.backfill_service.backfill_range, start_date, end_date)
            # lambda default argument trick to capture start_date and end_date
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
        QMessageBox.information(
            self, "Başarılı",
            f"{start_date} — {end_date} için {count} adet fiyat verisi indirildi."
        )

    def _on_backfill_error(self, err_tuple):
        exctype, value, tb_str = err_tuple
        QMessageBox.critical(self, "Hata", f"Veri çekme sırasında hata:\n{value}")


class CapitalDialog(QDialog):
    """Sermaye ekleme/çekme diyaloğu."""

    def __init__(self, current_capital: Decimal, parent=None):
        super().__init__(parent)
        self.current_capital = current_capital
        
        self.setWindowTitle("Sermaye Yönetimi")
        self.resize(350, 200)
        self.setModal(True)
        
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Mevcut sermaye
        lbl_current = QLabel(f"Mevcut Sermaye: ₺{self.current_capital:,.2f}")
        lbl_current.setStyleSheet("font-size: 14px; font-weight: bold; color: #f1f5f9;")
        layout.addWidget(lbl_current)
        
        form = QFormLayout()
        form.setSpacing(10)
        
        # İşlem türü
        self.combo_action = QComboBox()
        self.combo_action.addItems(["Sermaye Ekle", "Sermaye Çek"])
        self.combo_action.setStyleSheet("""
            QComboBox {
                background-color: #1e293b;
                color: #f1f5f9;
                border: 1px solid #334155;
                padding: 8px;
                border-radius: 6px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #f1f5f9;
                selection-background-color: #3b82f6;
            }
        """)
        form.addRow("İşlem:", self.combo_action)
        
        # Tutar
        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(0.01, 100000000)
        self.spin_amount.setValue(10000)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setSuffix(" TL")
        self.spin_amount.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #1e293b;
                color: #f1f5f9;
                border: 1px solid #334155;
                padding: 8px;
                border-radius: 6px;
            }
        """)
        form.addRow("Tutar:", self.spin_amount)
        
        layout.addLayout(form)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #f1f5f9;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        
        btn_confirm = QPushButton("Onayla")
        btn_confirm.clicked.connect(self.accept)
        btn_confirm.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_confirm)
        layout.addLayout(btn_layout)

    def get_result(self) -> Optional[Dict]:
        action = "deposit" if self.combo_action.currentIndex() == 0 else "withdraw"
        amount = Decimal(str(self.spin_amount.value()))
        
        if amount <= 0:
            return None
        
        return {
            "action": action,
            "amount": amount,
        }

class PortfolioRowDelegate(QStyledItemDelegate):
    """
    Tablo satırlarının sol kenarına kar/zarar durumuna göre 
    3px renkli border (indicator) çizen delegate.
    """
    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        
        # Sadece ilk kolonun (0) sol kenarına çiz
        if index.column() == 0:
            model = index.model()
            row = index.row()
            
            # Eğer Proxy model kullanılıyorsa, sourceRow/sourceModel alalım (ileride eklenebilir ihtimaline karşı)
            if hasattr(model, 'mapToSource'):
                source_index = model.mapToSource(index)
                model = model.sourceModel()
                row = source_index.row()
                
            if hasattr(model, 'get_position') and hasattr(model, '_price_map'):
                try:
                    position = model.get_position(row)
                    current_price = model._price_map.get(position.stock_id)
                    
                    # Varsayılan: Nötr gri
                    color = QColor("#555555")
                    
                    if current_price is not None:
                        pl = position.unrealized_pl(current_price)
                        if pl > 0:
                            color = QColor("#00C853")
                        elif pl < 0:
                            color = QColor("#FF1744")
                    
                    painter.save()
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(color)
                    painter.drawRect(option.rect.x(), option.rect.y(), 3, option.rect.height())
                    painter.restore()
                except Exception:
                    pass

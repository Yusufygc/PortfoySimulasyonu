# src/ui/widgets/model_portfolio_manager_dialog.py

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import date, datetime

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QFrame,
    QInputDialog,
    QDoubleSpinBox,
    QSpinBox,
    QDateEdit,
    QComboBox,
    QFormLayout,
    QGroupBox,
)
from PyQt5.QtCore import Qt, QDate, QThreadPool

from src.application.services.planning.model_portfolio_service import ModelPortfolioService
from src.domain.models.model_portfolio import ModelPortfolio
from src.ui.worker import Worker


class ModelPortfolioManagerDialog(QDialog):
    """
    Model Portföy yönetim diyaloğu.
    Portföy CRUD işlemleri, hisse alım/satım ve pozisyon görüntüleme.
    """

    def __init__(
        self,
        model_portfolio_service: ModelPortfolioService,
        price_lookup_func=None,
        parent=None,
    ):
        super().__init__(parent)
        self.model_portfolio_service = model_portfolio_service
        self.price_lookup_func = price_lookup_func
        self.current_portfolio_id: Optional[int] = None
        self.current_price_map: Dict[int, Decimal] = {}

        self.setWindowTitle("📊 Model Portföyler")
        self.resize(1100, 700)
        self.setModal(True)

        self._init_ui()
        self._load_portfolios()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(15)

        # Sol Panel: Portföy listesi
        left_panel = QFrame()
        left_panel.setObjectName("modelPortfolioLeftPanel")
        left_panel.setFixedWidth(280)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)

        # Başlık
        lbl_title = QLabel("Model Portföylerim")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f1f5f9;")
        left_layout.addWidget(lbl_title)

        # Liste widget
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.itemClicked.connect(self._on_portfolio_selected)
        left_layout.addWidget(self.list_widget)

        # Butonlar
        btn_layout = QHBoxLayout()
        
        self.btn_new = QPushButton("➕ Yeni")
        self.btn_new.setCursor(Qt.PointingHandCursor)
        self.btn_new.clicked.connect(self._on_new_portfolio)
        
        self.btn_edit = QPushButton("✏️ Düzenle")
        self.btn_edit.setCursor(Qt.PointingHandCursor)
        self.btn_edit.clicked.connect(self._on_edit_portfolio)
        self.btn_edit.setEnabled(False)
        
        self.btn_delete = QPushButton("🗑️ Sil")
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.clicked.connect(self._on_delete_portfolio)
        self.btn_delete.setEnabled(False)
        self.btn_delete.setStyleSheet("color: #ef4444;")

        btn_layout.addWidget(self.btn_new)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        left_layout.addLayout(btn_layout)

        # Sağ Panel: Portföy detayları
        right_panel = QFrame()
        right_panel.setObjectName("modelPortfolioRightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(15)

        # Başlık ve özet bilgiler
        header_layout = QHBoxLayout()
        
        self.lbl_portfolio_name = QLabel("Bir portföy seçin")
        self.lbl_portfolio_name.setStyleSheet("font-size: 18px; font-weight: bold; color: #f1f5f9;")
        header_layout.addWidget(self.lbl_portfolio_name)
        header_layout.addStretch()
        
        self.btn_refresh_prices = QPushButton("🔄 Fiyat Güncelle")
        self.btn_refresh_prices.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_prices.clicked.connect(self._on_refresh_prices)
        self.btn_refresh_prices.setEnabled(False)
        header_layout.addWidget(self.btn_refresh_prices)
        
        right_layout.addLayout(header_layout)

        # Özet kartları
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(15)

        # Başlangıç Sermayesi
        self.card_initial = self._create_summary_card("Başlangıç", "₺ 0")
        summary_layout.addWidget(self.card_initial)

        # Kalan Nakit
        self.card_cash = self._create_summary_card("Nakit", "₺ 0")
        summary_layout.addWidget(self.card_cash)

        # Portföy Değeri
        self.card_value = self._create_summary_card("Portföy Değeri", "₺ 0")
        summary_layout.addWidget(self.card_value)

        # Kar/Zarar
        self.card_pl = self._create_summary_card("Kar/Zarar", "₺ 0")
        summary_layout.addWidget(self.card_pl)

        right_layout.addLayout(summary_layout)

        # Pozisyonlar tablosu
        lbl_positions = QLabel("Pozisyonlar")
        lbl_positions.setStyleSheet("font-size: 14px; font-weight: bold; color: #94a3b8;")
        right_layout.addWidget(lbl_positions)

        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(7)
        self.positions_table.setHorizontalHeaderLabels([
            "Ticker", "Hisse", "Lot", "Ort. Maliyet", "Güncel Fiyat", "Değer", "K/Z"
        ])
        self.positions_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.positions_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.positions_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.positions_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.positions_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.positions_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.positions_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.positions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.positions_table.setAlternatingRowColors(True)
        self.positions_table.verticalHeader().setVisible(False)
        right_layout.addWidget(self.positions_table)

        # İşlem butonları
        trade_btn_layout = QHBoxLayout()
        
        self.btn_buy = QPushButton("📈 Hisse Al")
        self.btn_buy.setCursor(Qt.PointingHandCursor)
        self.btn_buy.clicked.connect(lambda: self._on_trade("BUY"))
        self.btn_buy.setEnabled(False)
        self.btn_buy.setObjectName("primaryButton")
        self.btn_buy.setStyleSheet("background-color: #10b981;")
        
        self.btn_sell = QPushButton("📉 Hisse Sat")
        self.btn_sell.setCursor(Qt.PointingHandCursor)
        self.btn_sell.clicked.connect(lambda: self._on_trade("SELL"))
        self.btn_sell.setEnabled(False)
        self.btn_sell.setStyleSheet("background-color: #ef4444;")
        
        trade_btn_layout.addStretch()
        trade_btn_layout.addWidget(self.btn_buy)
        trade_btn_layout.addWidget(self.btn_sell)
        right_layout.addLayout(trade_btn_layout)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)

    def _create_summary_card(self, title: str, value: str) -> QFrame:
        """Özet kartı oluşturur."""
        card = QFrame()
        card.setObjectName("summaryCard")
        card.setStyleSheet("""
            QFrame#summaryCard {
                background-color: #1e293b;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #94a3b8; font-size: 12px;")
        
        lbl_value = QLabel(value)
        lbl_value.setStyleSheet("color: #f1f5f9; font-size: 16px; font-weight: bold;")
        lbl_value.setObjectName("valueLabel")
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        
        return card

    def _load_portfolios(self):
        """Portföyleri yükle ve listele."""
        self.list_widget.clear()
        portfolios = self.model_portfolio_service.get_all_portfolios()

        for pf in portfolios:
            trade_count = self.model_portfolio_service.get_trade_count(pf.id)
            item = QListWidgetItem(f"{pf.name} ({trade_count} işlem)")
            item.setData(Qt.UserRole, pf)
            self.list_widget.addItem(item)

    def _on_portfolio_selected(self, item: QListWidgetItem):
        """Portföy seçildiğinde çağrılır."""
        portfolio: ModelPortfolio = item.data(Qt.UserRole)
        self.current_portfolio_id = portfolio.id
        
        self.lbl_portfolio_name.setText(portfolio.name)
        
        self.btn_edit.setEnabled(True)
        self.btn_delete.setEnabled(True)
        self.btn_buy.setEnabled(True)
        self.btn_sell.setEnabled(True)
        self.btn_refresh_prices.setEnabled(True)

        self._update_portfolio_view()

    def _update_portfolio_view(self):
        """Portföy görünümünü güncelle."""
        if self.current_portfolio_id is None:
            return

        # Özet bilgileri güncelle
        summary = self.model_portfolio_service.get_portfolio_summary(
            self.current_portfolio_id,
            self.current_price_map,
        )

        # Kartları güncelle
        self.card_initial.findChild(QLabel, "valueLabel").setText(
            f"₺ {summary['initial_cash']:,.2f}"
        )
        self.card_cash.findChild(QLabel, "valueLabel").setText(
            f"₺ {summary['remaining_cash']:,.2f}"
        )
        self.card_value.findChild(QLabel, "valueLabel").setText(
            f"₺ {summary['total_value']:,.2f}"
        )
        
        pl_text = f"₺ {summary['profit_loss']:+,.2f} ({summary['profit_loss_pct']:+.2f}%)"
        pl_color = "#10b981" if summary['profit_loss'] >= 0 else "#ef4444"
        self.card_pl.findChild(QLabel, "valueLabel").setText(pl_text)
        self.card_pl.findChild(QLabel, "valueLabel").setStyleSheet(
            f"color: {pl_color}; font-size: 16px; font-weight: bold;"
        )

        # Pozisyonları güncelle
        self._load_positions()

    def _load_positions(self):
        """Pozisyonları tabloya yükle."""
        self.positions_table.setRowCount(0)
        
        if self.current_portfolio_id is None:
            return

        positions = self.model_portfolio_service.get_positions_with_details(
            self.current_portfolio_id,
            self.current_price_map,
        )
        
        for i, pos in enumerate(positions):
            self.positions_table.insertRow(i)
            
            # Ticker
            self.positions_table.setItem(i, 0, QTableWidgetItem(pos["ticker"]))
            
            # Hisse adı
            self.positions_table.setItem(i, 1, QTableWidgetItem(pos["name"] or ""))
            
            # Lot
            self.positions_table.setItem(i, 2, QTableWidgetItem(str(pos["quantity"])))
            
            # Ortalama maliyet
            self.positions_table.setItem(i, 3, QTableWidgetItem(f"₺ {pos['avg_cost']:.2f}"))
            
            # Güncel fiyat
            if pos["current_price"]:
                self.positions_table.setItem(i, 4, QTableWidgetItem(f"₺ {pos['current_price']:.2f}"))
            else:
                self.positions_table.setItem(i, 4, QTableWidgetItem("-"))
            
            # Değer
            if pos["current_value"]:
                self.positions_table.setItem(i, 5, QTableWidgetItem(f"₺ {pos['current_value']:,.2f}"))
            else:
                self.positions_table.setItem(i, 5, QTableWidgetItem("-"))
            
            # Kar/Zarar
            if pos["profit_loss"] is not None:
                pl_item = QTableWidgetItem(f"₺ {pos['profit_loss']:+,.2f}")
                if pos["profit_loss"] >= 0:
                    pl_item.setForeground(Qt.green)
                else:
                    pl_item.setForeground(Qt.red)
                self.positions_table.setItem(i, 6, pl_item)
            else:
                self.positions_table.setItem(i, 6, QTableWidgetItem("-"))

    def _on_new_portfolio(self):
        """Yeni portföy oluştur."""
        dialog = NewPortfolioDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return

        result = dialog.get_result()
        if not result:
            return

        try:
            self.model_portfolio_service.create_portfolio(
                name=result["name"],
                description=result["description"],
                initial_cash=result["initial_cash"],
            )
            self._load_portfolios()
            QMessageBox.information(self, "Başarılı", f"'{result['name']}' portföyü oluşturuldu.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Portföy oluşturulamadı:\n{e}")

    def _on_edit_portfolio(self):
        """Seçili portföyü düzenle."""
        if self.current_portfolio_id is None:
            return

        current_item = self.list_widget.currentItem()
        if not current_item:
            return

        portfolio: ModelPortfolio = current_item.data(Qt.UserRole)

        dialog = NewPortfolioDialog(self, portfolio)
        if dialog.exec_() != QDialog.Accepted:
            return

        result = dialog.get_result()
        if not result:
            return

        try:
            self.model_portfolio_service.update_portfolio(
                portfolio_id=self.current_portfolio_id,
                name=result["name"],
                description=result["description"],
                initial_cash=result["initial_cash"],
            )
            self._load_portfolios()
            self.lbl_portfolio_name.setText(result["name"])
            self._update_portfolio_view()
            QMessageBox.information(self, "Başarılı", "Portföy güncellendi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Portföy güncellenemedi:\n{e}")

    def _on_delete_portfolio(self):
        """Seçili portföyü sil."""
        if self.current_portfolio_id is None:
            return

        reply = QMessageBox.question(
            self,
            "Portföy Sil",
            "Bu portföyü silmek istediğinizden emin misiniz?\nTüm işlemler de silinecek.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            self.model_portfolio_service.delete_portfolio(self.current_portfolio_id)
            self.current_portfolio_id = None
            self._load_portfolios()
            self._clear_right_panel()
            QMessageBox.information(self, "Başarılı", "Portföy silindi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Portföy silinemedi:\n{e}")

    def _clear_right_panel(self):
        """Sağ paneli temizle."""
        self.lbl_portfolio_name.setText("Bir portföy seçin")
        self.positions_table.setRowCount(0)
        self.btn_edit.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self.btn_buy.setEnabled(False)
        self.btn_sell.setEnabled(False)
        self.btn_refresh_prices.setEnabled(False)
        
        # Kartları sıfırla
        for card in [self.card_initial, self.card_cash, self.card_value, self.card_pl]:
            card.findChild(QLabel, "valueLabel").setText("₺ 0")

    def _on_trade(self, side: str):
        """Hisse al/sat diyaloğunu aç."""
        if self.current_portfolio_id is None:
            return

        dialog = TradeInputDialog(
            side=side,
            price_lookup_func=self.price_lookup_func,
            parent=self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return

        result = dialog.get_result()
        if not result:
            return

        try:
            self.model_portfolio_service.add_trade_by_ticker(
                portfolio_id=self.current_portfolio_id,
                ticker=result["ticker"],
                side=side,
                quantity=result["quantity"],
                price=result["price"],
                trade_date=result["trade_date"],
            )
            self._load_portfolios()
            self._update_portfolio_view()
            
            action = "alındı" if side == "BUY" else "satıldı"
            QMessageBox.information(
                self, 
                "Başarılı", 
                f"{result['quantity']} lot {result['ticker']} {action}."
            )
        except ValueError as e:
            QMessageBox.warning(self, "Uyarı", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"İşlem gerçekleştirilemedi:\n{e}")

    def _on_refresh_prices(self):
        """Fiyatları güncelle."""
        if self.current_portfolio_id is None:
            return

        positions = self.model_portfolio_service.get_positions(self.current_portfolio_id)
        if not positions:
            QMessageBox.information(self, "Bilgi", "Güncellenecek pozisyon yok.")
            return

        if not self.price_lookup_func:
            QMessageBox.warning(self, "Uyarı", "Fiyat sorgulama fonksiyonu mevcut değil.")
            return

        # Pozisyonlardaki hisselerin fiyatlarını al
        from src.domain.models.stock import Stock
        positions_details = self.model_portfolio_service.get_positions_with_details(
            self.current_portfolio_id
        )

        updated_count = 0
        for pos in positions_details:
            ticker = pos["ticker"]
            try:
                result = self.price_lookup_func(ticker)
                if result:
                    self.current_price_map[pos["stock_id"]] = result.price
                    updated_count += 1
            except Exception as e:
                logger.error(f"Fiyat alınamadı: {ticker} - {e}")

        self._update_portfolio_view()
        QMessageBox.information(
            self, 
            "Fiyatlar Güncellendi", 
            f"{updated_count} hisse için fiyat güncellendi."
        )


class NewPortfolioDialog(QDialog):
    """Yeni portföy oluşturma/düzenleme diyaloğu."""

    def __init__(self, parent=None, portfolio: Optional[ModelPortfolio] = None):
        super().__init__(parent)
        self.portfolio = portfolio
        self.is_edit = portfolio is not None

        self.setWindowTitle("Portföy Düzenle" if self.is_edit else "Yeni Portföy")
        self.resize(400, 250)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Portföy adı
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Örn: Agresif Büyüme")
        if self.is_edit:
            self.txt_name.setText(self.portfolio.name)
        form_layout.addRow("Portföy Adı:", self.txt_name)

        # Açıklama
        self.txt_description = QLineEdit()
        self.txt_description.setPlaceholderText("Opsiyonel")
        if self.is_edit and self.portfolio.description:
            self.txt_description.setText(self.portfolio.description)
        form_layout.addRow("Açıklama:", self.txt_description)

        # Başlangıç sermayesi
        self.spin_cash = QDoubleSpinBox()
        self.spin_cash.setRange(1000, 100000000)
        self.spin_cash.setValue(100000 if not self.is_edit else float(self.portfolio.initial_cash))
        self.spin_cash.setDecimals(2)
        self.spin_cash.setSuffix(" TL")
        self.spin_cash.setSingleStep(10000)
        form_layout.addRow("Başlangıç Sermayesi:", self.spin_cash)

        layout.addLayout(form_layout)

        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("Kaydet")
        btn_save.setObjectName("primaryButton")
        btn_save.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def get_result(self) -> Optional[Dict[str, Any]]:
        name = self.txt_name.text().strip()
        if not name:
            return None

        return {
            "name": name,
            "description": self.txt_description.text().strip() or None,
            "initial_cash": Decimal(str(self.spin_cash.value())),
        }


class TradeInputDialog(QDialog):
    """Hisse alım/satım giriş diyaloğu."""

    def __init__(self, side: str, price_lookup_func=None, parent=None):
        super().__init__(parent)
        self.side = side
        self.price_lookup_func = price_lookup_func

        title = "📈 Hisse Al" if side == "BUY" else "📉 Hisse Sat"
        self.setWindowTitle(title)
        self.resize(400, 300)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Ticker
        ticker_layout = QHBoxLayout()
        self.txt_ticker = QLineEdit()
        self.txt_ticker.setPlaceholderText("Örn: ASELS veya ASELS.IS")
        ticker_layout.addWidget(self.txt_ticker)
        
        btn_lookup = QPushButton("🔍")
        btn_lookup.setFixedWidth(40)
        btn_lookup.setCursor(Qt.PointingHandCursor)
        btn_lookup.clicked.connect(self._on_lookup_price)
        ticker_layout.addWidget(btn_lookup)
        
        form_layout.addRow("Ticker:", ticker_layout)

        # Lot sayısı
        self.spin_quantity = QSpinBox()
        self.spin_quantity.setRange(1, 1000000)
        self.spin_quantity.setValue(100)
        self.spin_quantity.valueChanged.connect(self._update_total)
        form_layout.addRow("Lot Sayısı:", self.spin_quantity)

        # Fiyat
        self.spin_price = QDoubleSpinBox()
        self.spin_price.setRange(0.01, 100000)
        self.spin_price.setValue(10)
        self.spin_price.setDecimals(4)
        self.spin_price.setSuffix(" TL")
        self.spin_price.valueChanged.connect(self._update_total)
        form_layout.addRow("Birim Fiyat:", self.spin_price)

        # Tarih
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        form_layout.addRow("İşlem Tarihi:", self.date_edit)

        # Toplam tutar
        self.lbl_total = QLabel("₺ 1,000.00")
        self.lbl_total.setStyleSheet("font-size: 14px; font-weight: bold; color: #f1f5f9;")
        form_layout.addRow("Toplam Tutar:", self.lbl_total)

        layout.addLayout(form_layout)

        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.clicked.connect(self.reject)
        
        action_text = "Al" if self.side == "BUY" else "Sat"
        btn_action = QPushButton(action_text)
        btn_action.setObjectName("primaryButton")
        if self.side == "BUY":
            btn_action.setStyleSheet("background-color: #10b981;")
        else:
            btn_action.setStyleSheet("background-color: #ef4444;")
        btn_action.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_action)
        layout.addLayout(btn_layout)

        self._update_total()

    def _update_total(self):
        """Toplam tutarı güncelle."""
        quantity = self.spin_quantity.value()
        price = Decimal(str(self.spin_price.value()))
        total = price * Decimal(quantity)
        self.lbl_total.setText(f"₺ {total:,.2f}")

    def _on_lookup_price(self):
        """Fiyat sorgula (Asenkron)."""
        if not self.price_lookup_func:
            QMessageBox.warning(self, "Uyarı", "Fiyat sorgulama mevcut değil.")
            return

        ticker = self.txt_ticker.text().strip()
        if not ticker:
            QMessageBox.warning(self, "Uyarı", "Lütfen ticker girin.")
            return

        self.lbl_total.setText("⏳ Yükleniyor...")

        worker = Worker(self.price_lookup_func, ticker)
        worker.signals.result.connect(lambda res: self._on_lookup_price_result(res, ticker))
        worker.signals.error.connect(self._on_lookup_price_error)
        QThreadPool.globalInstance().start(worker)

    def _on_lookup_price_result(self, result, ticker):
        if result:
            self.spin_price.setValue(float(result.price))
            self._update_total()
            QMessageBox.information(
                self, 
                "Fiyat Bulundu", 
                f"{ticker.upper()}: ₺ {result.price:.4f}\nKaynak: {result.source}"
            )
        else:
            self._update_total()
            QMessageBox.warning(self, "Uyarı", f"{ticker} için fiyat bulunamadı.")

    def _on_lookup_price_error(self, err_tuple):
        self._update_total()
        QMessageBox.critical(self, "Hata", "Fiyat sorgulanırken ağ hatası.")

    def get_result(self) -> Optional[Dict[str, Any]]:
        ticker = self.txt_ticker.text().strip()
        if not ticker:
            return None

        return {
            "ticker": ticker.upper(),
            "quantity": self.spin_quantity.value(),
            "price": Decimal(str(self.spin_price.value())),
            "trade_date": self.date_edit.date().toPyDate(),
        }

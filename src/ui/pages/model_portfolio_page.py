# src/ui/pages/model_portfolio_page.py

from __future__ import annotations

from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import date

from PyQt5.QtWidgets import (
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
    QDialog,
    QFormLayout,
    QDoubleSpinBox,
    QSpinBox,
    QDateEdit,
)
from PyQt5.QtCore import Qt, QDate

from .base_page import BasePage
from src.domain.models.model_portfolio import ModelPortfolio


class ModelPortfolioPage(BasePage):
    """
    Model Portföy sayfası.
    Portföy CRUD, hisse alım/satım ve pozisyon takibi.
    """

    def __init__(self, model_portfolio_service, price_lookup_func=None, parent=None):
        super().__init__(parent)
        self.page_title = "Model Portföyler"
        self.model_portfolio_service = model_portfolio_service
        self.price_lookup_func = price_lookup_func
        self.current_portfolio_id: Optional[int] = None
        self.current_price_map: Dict[int, Decimal] = {}
        
        self._init_ui()

    def _init_ui(self):
        # Başlık
        header_layout = QHBoxLayout()
        lbl_title = QLabel("📊 Model Portföyler")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #f1f5f9;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        self.main_layout.addLayout(header_layout)

        # Ana içerik
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Sol Panel: Portföy listesi
        left_panel = QFrame()
        left_panel.setObjectName("leftPanel")
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(15, 15, 15, 15)
        left_layout.setSpacing(10)

        lbl_portfolios = QLabel("Portföylerim")
        lbl_portfolios.setStyleSheet("font-size: 14px; font-weight: bold; color: #94a3b8;")
        left_layout.addWidget(lbl_portfolios)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.itemClicked.connect(self._on_portfolio_selected)
        left_layout.addWidget(self.list_widget)

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

        # Sağ Panel: Detaylar
        right_panel = QFrame()
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(15)

        # Başlık ve fiyat güncelle
        header_layout2 = QHBoxLayout()
        self.lbl_portfolio_name = QLabel("Bir portföy seçin")
        self.lbl_portfolio_name.setStyleSheet("font-size: 18px; font-weight: bold; color: #f1f5f9;")
        header_layout2.addWidget(self.lbl_portfolio_name)
        header_layout2.addStretch()
        
        self.btn_refresh = QPushButton("🔄 Fiyat Güncelle")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self._on_refresh_prices)
        self.btn_refresh.setEnabled(False)
        header_layout2.addWidget(self.btn_refresh)
        right_layout.addLayout(header_layout2)

        # Özet kartları
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)

        self.card_initial = self._create_card("Başlangıç", "₺ 0")
        self.card_cash = self._create_card("Nakit", "₺ 0")
        self.card_value = self._create_card("Değer", "₺ 0")
        self.card_pl = self._create_card("K/Z", "₺ 0")

        cards_layout.addWidget(self.card_initial)
        cards_layout.addWidget(self.card_cash)
        cards_layout.addWidget(self.card_value)
        cards_layout.addWidget(self.card_pl)
        right_layout.addLayout(cards_layout)

        # Pozisyonlar tablosu
        lbl_positions = QLabel("Pozisyonlar")
        lbl_positions.setStyleSheet("font-size: 14px; font-weight: bold; color: #94a3b8;")
        right_layout.addWidget(lbl_positions)

        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(7)
        self.positions_table.setHorizontalHeaderLabels([
            "Ticker", "Hisse", "Lot", "Ort. Maliyet", "Güncel", "Değer", "K/Z"
        ])
        for i in range(7):
            mode = QHeaderView.Stretch if i == 1 else QHeaderView.ResizeToContents
            self.positions_table.horizontalHeader().setSectionResizeMode(i, mode)
        self.positions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.positions_table.setAlternatingRowColors(True)
        self.positions_table.verticalHeader().setVisible(False)
        right_layout.addWidget(self.positions_table)

        # Al/Sat butonları
        trade_layout = QHBoxLayout()
        trade_layout.addStretch()
        
        self.btn_buy = QPushButton("📈 Hisse Al")
        self.btn_buy.setCursor(Qt.PointingHandCursor)
        self.btn_buy.clicked.connect(lambda: self._on_trade("BUY"))
        self.btn_buy.setEnabled(False)
        self.btn_buy.setStyleSheet("background-color: #10b981; color: white; padding: 8px 16px;")
        
        self.btn_sell = QPushButton("📉 Hisse Sat")
        self.btn_sell.setCursor(Qt.PointingHandCursor)
        self.btn_sell.clicked.connect(lambda: self._on_trade("SELL"))
        self.btn_sell.setEnabled(False)
        self.btn_sell.setStyleSheet("background-color: #ef4444; color: white; padding: 8px 16px;")
        
        trade_layout.addWidget(self.btn_buy)
        trade_layout.addWidget(self.btn_sell)
        right_layout.addLayout(trade_layout)

        content_layout.addWidget(left_panel)
        content_layout.addWidget(right_panel, 1)
        self.main_layout.addLayout(content_layout)

    def _create_card(self, title: str, value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("summaryCard")
        card.setStyleSheet("""
            QFrame#summaryCard {
                background-color: #1e293b;
                border-radius: 8px;
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

    def on_page_enter(self):
        self.refresh_data()

    def refresh_data(self):
        self._load_portfolios()

    def _load_portfolios(self):
        self.list_widget.clear()
        portfolios = self.model_portfolio_service.get_all_portfolios()

        for pf in portfolios:
            trade_count = self.model_portfolio_service.get_trade_count(pf.id)
            item = QListWidgetItem(f"{pf.name} ({trade_count} işlem)")
            item.setData(Qt.UserRole, pf)
            self.list_widget.addItem(item)

    def _on_portfolio_selected(self, item: QListWidgetItem):
        portfolio: ModelPortfolio = item.data(Qt.UserRole)
        self.current_portfolio_id = portfolio.id
        
        self.lbl_portfolio_name.setText(portfolio.name)
        
        self.btn_edit.setEnabled(True)
        self.btn_delete.setEnabled(True)
        self.btn_buy.setEnabled(True)
        self.btn_sell.setEnabled(True)
        self.btn_refresh.setEnabled(True)

        self._update_view()

    def _update_view(self):
        if self.current_portfolio_id is None:
            return

        summary = self.model_portfolio_service.get_portfolio_summary(
            self.current_portfolio_id, self.current_price_map
        )

        self.card_initial.findChild(QLabel, "valueLabel").setText(f"₺ {summary['initial_cash']:,.2f}")
        self.card_cash.findChild(QLabel, "valueLabel").setText(f"₺ {summary['remaining_cash']:,.2f}")
        self.card_value.findChild(QLabel, "valueLabel").setText(f"₺ {summary['total_value']:,.2f}")
        
        pl = summary['profit_loss']
        pl_text = f"₺ {pl:+,.2f}"
        pl_color = "#10b981" if pl >= 0 else "#ef4444"
        self.card_pl.findChild(QLabel, "valueLabel").setText(pl_text)
        self.card_pl.findChild(QLabel, "valueLabel").setStyleSheet(
            f"color: {pl_color}; font-size: 16px; font-weight: bold;"
        )

        self._load_positions()

    def _load_positions(self):
        self.positions_table.setRowCount(0)
        
        if self.current_portfolio_id is None:
            return

        positions = self.model_portfolio_service.get_positions_with_details(
            self.current_portfolio_id, self.current_price_map
        )
        
        for i, pos in enumerate(positions):
            self.positions_table.insertRow(i)
            
            self.positions_table.setItem(i, 0, QTableWidgetItem(pos["ticker"]))
            self.positions_table.setItem(i, 1, QTableWidgetItem(pos["name"] or ""))
            self.positions_table.setItem(i, 2, QTableWidgetItem(str(pos["quantity"])))
            self.positions_table.setItem(i, 3, QTableWidgetItem(f"₺ {pos['avg_cost']:.2f}"))
            
            if pos["current_price"]:
                self.positions_table.setItem(i, 4, QTableWidgetItem(f"₺ {pos['current_price']:.2f}"))
                self.positions_table.setItem(i, 5, QTableWidgetItem(f"₺ {pos['current_value']:,.2f}"))
                
                pl_item = QTableWidgetItem(f"₺ {pos['profit_loss']:+,.2f}")
                pl_item.setForeground(Qt.green if pos["profit_loss"] >= 0 else Qt.red)
                self.positions_table.setItem(i, 6, pl_item)
            else:
                self.positions_table.setItem(i, 4, QTableWidgetItem("-"))
                self.positions_table.setItem(i, 5, QTableWidgetItem("-"))
                self.positions_table.setItem(i, 6, QTableWidgetItem("-"))

    def _on_new_portfolio(self):
        dialog = PortfolioInputDialog(self)
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
            QMessageBox.critical(self, "Hata", f"Portföy oluşturulamadı: {e}")

    def _on_edit_portfolio(self):
        if self.current_portfolio_id is None:
            return

        current_item = self.list_widget.currentItem()
        if not current_item:
            return

        portfolio: ModelPortfolio = current_item.data(Qt.UserRole)

        dialog = PortfolioInputDialog(self, portfolio)
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
            self._update_view()
            QMessageBox.information(self, "Başarılı", "Portföy güncellendi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Portföy güncellenemedi: {e}")

    def _on_delete_portfolio(self):
        if self.current_portfolio_id is None:
            return

        reply = QMessageBox.question(
            self, "Portföy Sil", "Bu portföyü silmek istediğinizden emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
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
            QMessageBox.critical(self, "Hata", f"Portföy silinemedi: {e}")

    def _clear_right_panel(self):
        self.lbl_portfolio_name.setText("Bir portföy seçin")
        self.positions_table.setRowCount(0)
        self.btn_edit.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self.btn_buy.setEnabled(False)
        self.btn_sell.setEnabled(False)
        self.btn_refresh.setEnabled(False)
        
        for card in [self.card_initial, self.card_cash, self.card_value, self.card_pl]:
            card.findChild(QLabel, "valueLabel").setText("₺ 0")

    def _on_trade(self, side: str):
        if self.current_portfolio_id is None:
            return

        dialog = TradeInputDialog(side, self.price_lookup_func, self)
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
            self._update_view()
            
            action = "alındı" if side == "BUY" else "satıldı"
            QMessageBox.information(self, "Başarılı", f"{result['quantity']} lot {result['ticker']} {action}.")
        except ValueError as e:
            QMessageBox.warning(self, "Uyarı", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"İşlem gerçekleştirilemedi: {e}")

    def _on_refresh_prices(self):
        if self.current_portfolio_id is None:
            return

        positions = self.model_portfolio_service.get_positions(self.current_portfolio_id)
        if not positions:
            QMessageBox.information(self, "Bilgi", "Güncellenecek pozisyon yok.")
            return

        if not self.price_lookup_func:
            QMessageBox.warning(self, "Uyarı", "Fiyat sorgulama fonksiyonu mevcut değil.")
            return

        positions_details = self.model_portfolio_service.get_positions_with_details(self.current_portfolio_id)

        updated_count = 0
        for pos in positions_details:
            ticker = pos["ticker"]
            try:
                result = self.price_lookup_func(ticker)
                if result:
                    self.current_price_map[pos["stock_id"]] = result.price
                    updated_count += 1
            except Exception as e:
                print(f"Fiyat alınamadı: {ticker} - {e}")

        self._update_view()
        QMessageBox.information(self, "Fiyatlar Güncellendi", f"{updated_count} hisse için fiyat güncellendi.")


class PortfolioInputDialog(QDialog):
    """Portföy oluşturma/düzenleme diyaloğu."""

    def __init__(self, parent=None, portfolio: Optional[ModelPortfolio] = None):
        super().__init__(parent)
        self.portfolio = portfolio
        self.is_edit = portfolio is not None

        self.setWindowTitle("Portföy Düzenle" if self.is_edit else "Yeni Portföy")
        self.resize(400, 200)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_name = QLineEdit()
        if self.is_edit:
            self.txt_name.setText(self.portfolio.name)
        form.addRow("Adı:", self.txt_name)

        self.txt_desc = QLineEdit()
        if self.is_edit and self.portfolio.description:
            self.txt_desc.setText(self.portfolio.description)
        form.addRow("Açıklama:", self.txt_desc)

        self.spin_cash = QDoubleSpinBox()
        self.spin_cash.setRange(1000, 100000000)
        self.spin_cash.setValue(100000 if not self.is_edit else float(self.portfolio.initial_cash))
        self.spin_cash.setDecimals(2)
        self.spin_cash.setSuffix(" TL")
        form.addRow("Sermaye:", self.spin_cash)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Kaydet")
        btn_save.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def get_result(self):
        name = self.txt_name.text().strip()
        if not name:
            return None
        return {
            "name": name,
            "description": self.txt_desc.text().strip() or None,
            "initial_cash": Decimal(str(self.spin_cash.value())),
        }


class TradeInputDialog(QDialog):
    """Al/Sat diyaloğu."""

    def __init__(self, side: str, price_lookup_func=None, parent=None):
        super().__init__(parent)
        self.side = side
        self.price_lookup_func = price_lookup_func

        self.setWindowTitle("📈 Hisse Al" if side == "BUY" else "📉 Hisse Sat")
        self.resize(350, 250)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Ticker
        ticker_layout = QHBoxLayout()
        self.txt_ticker = QLineEdit()
        self.txt_ticker.setPlaceholderText("Örn: ASELS")
        ticker_layout.addWidget(self.txt_ticker)
        
        btn_lookup = QPushButton("🔍")
        btn_lookup.setFixedWidth(40)
        btn_lookup.clicked.connect(self._on_lookup)
        ticker_layout.addWidget(btn_lookup)
        form.addRow("Ticker:", ticker_layout)

        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 1000000)
        self.spin_qty.setValue(100)
        form.addRow("Lot:", self.spin_qty)

        self.spin_price = QDoubleSpinBox()
        self.spin_price.setRange(0.01, 100000)
        self.spin_price.setValue(10)
        self.spin_price.setDecimals(4)
        self.spin_price.setSuffix(" TL")
        form.addRow("Fiyat:", self.spin_price)

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        form.addRow("Tarih:", self.date_edit)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.clicked.connect(self.reject)
        
        btn_action = QPushButton("Al" if self.side == "BUY" else "Sat")
        btn_action.setStyleSheet(
            f"background-color: {'#10b981' if self.side == 'BUY' else '#ef4444'}; color: white;"
        )
        btn_action.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_action)
        layout.addLayout(btn_layout)

    def _on_lookup(self):
        if not self.price_lookup_func:
            return
        ticker = self.txt_ticker.text().strip()
        if not ticker:
            return
        try:
            result = self.price_lookup_func(ticker)
            if result:
                self.spin_price.setValue(float(result.price))
        except:
            pass

    def get_result(self):
        ticker = self.txt_ticker.text().strip()
        if not ticker:
            return None
        return {
            "ticker": ticker.upper(),
            "quantity": self.spin_qty.value(),
            "price": Decimal(str(self.spin_price.value())),
            "trade_date": self.date_edit.date().toPyDate(),
        }

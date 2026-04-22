# src/ui/pages/model_portfolio_page.py

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

from typing import Optional, Dict
from decimal import Decimal

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QMessageBox, QDialog, QFormLayout,
    QDoubleSpinBox, QSpinBox, QDateEdit, QLineEdit,
)
from PyQt5.QtCore import Qt, QDate

from .base_page import BasePage
from src.domain.models.model_portfolio import ModelPortfolio
from src.ui.widgets.cards import InfoCard
from src.ui.widgets.tables import PositionsTable
from src.ui.widgets.panels import PortfolioListPanel
from src.ui.widgets.toast import Toast
from src.ui.widgets.animated_button import AnimatedButton


class ModelPortfolioPage(BasePage):
    """
    Model Portföy sayfası — koordinatör katmanı.
    Görsel yapı PortfolioListPanel, InfoCard ve PositionsTable widget'larına devredilmiştir.
    Bu sınıf yalnızca iş mantığını ve servis çağrılarını koordine eder.
    """

    def __init__(self, container, price_lookup_func=None, parent=None):
        super().__init__(parent)
        self.container = container
        self.page_title = "Model Portföyler"
        self.model_portfolio_service = container.model_portfolio_service
        self.price_lookup_func = price_lookup_func
        self.current_portfolio_id: Optional[int] = None
        self.current_price_map: Dict[int, Decimal] = {}
        self._init_ui()

    # ------------------------------------------------------------------
    # UI Kurulumu
    # ------------------------------------------------------------------

    def _init_ui(self):
        # Başlık
        header = QHBoxLayout()
        lbl_title = QLabel("📊 Model Portföyler")
        lbl_title.setProperty("cssClass", "pageTitle")
        header.addWidget(lbl_title)
        header.addStretch()
        self.main_layout.addLayout(header)

        content = QHBoxLayout()
        content.setSpacing(20)
        content.addWidget(self._build_left_panel())
        content.addWidget(self._build_right_panel(), 1)
        self.main_layout.addLayout(content)

    def _build_left_panel(self) -> PortfolioListPanel:
        """Sol panel: portföy listesi ve CRUD butonları."""
        self.list_panel = PortfolioListPanel()
        self.list_panel.portfolio_selected.connect(self._on_portfolio_selected)
        self.list_panel.new_requested.connect(self._on_new_portfolio)
        self.list_panel.edit_requested.connect(self._on_edit_portfolio)
        self.list_panel.delete_requested.connect(self._on_delete_portfolio)
        return self.list_panel

    def _build_right_panel(self) -> QFrame:
        """Sağ panel: özet kartları, pozisyon tablosu ve Al/Sat butonları."""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Başlık + Fiyat Güncelle
        header = QHBoxLayout()
        self.lbl_portfolio_name = QLabel("Bir portföy seçin")
        self.lbl_portfolio_name.setProperty("cssClass", "panelTitleLarge")
        header.addWidget(self.lbl_portfolio_name)
        header.addStretch()

        self.btn_refresh = AnimatedButton("🔄 Fiyat Güncelle")
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.clicked.connect(self._on_refresh_prices)
        header.addWidget(self.btn_refresh)
        layout.addLayout(header)

        # Özet kartları
        cards_row = QHBoxLayout()
        cards_row.setSpacing(15)
        self.card_initial = InfoCard("Başlangıç", "₺ 0")
        self.card_cash    = InfoCard("Nakit",      "₺ 0")
        self.card_value   = InfoCard("Değer",      "₺ 0")
        self.card_pl      = InfoCard("K/Z",        "₺ 0")
        for card in (self.card_initial, self.card_cash, self.card_value, self.card_pl):
            cards_row.addWidget(card)
        layout.addLayout(cards_row)

        # Pozisyonlar tablosu
        lbl_pos = QLabel("Pozisyonlar")
        lbl_pos.setProperty("cssClass", "panelTitle")
        layout.addWidget(lbl_pos)

        self.positions_table = PositionsTable()
        layout.addWidget(self.positions_table)

        # Al/Sat butonları
        trade_row = QHBoxLayout()
        trade_row.addStretch()

        self.btn_buy = AnimatedButton("📈 Hisse Al")
        self.btn_buy.setEnabled(False)
        self.btn_buy.setProperty("cssClass", "successButton")
        self.btn_buy.clicked.connect(lambda: self._on_trade("BUY"))

        self.btn_sell = AnimatedButton("📉 Hisse Sat")
        self.btn_sell.setEnabled(False)
        self.btn_sell.setProperty("cssClass", "dangerButton")
        self.btn_sell.clicked.connect(lambda: self._on_trade("SELL"))

        trade_row.addWidget(self.btn_buy)
        trade_row.addWidget(self.btn_sell)
        layout.addLayout(trade_row)

        return panel

    # ------------------------------------------------------------------
    # Sayfa Yaşam Döngüsü
    # ------------------------------------------------------------------

    def on_page_enter(self):
        self.refresh_data()

    def refresh_data(self):
        self._load_portfolios()

    def _load_portfolios(self):
        portfolios = self.model_portfolio_service.get_all_portfolios()
        self.list_panel.refresh(
            portfolios,
            trade_count_func=self.model_portfolio_service.get_trade_count,
        )

    # ------------------------------------------------------------------
    # Portföy Seçimi ve Görünüm Güncelleme
    # ------------------------------------------------------------------

    def _on_portfolio_selected(self, portfolio: ModelPortfolio):
        self.current_portfolio_id = portfolio.id
        self.lbl_portfolio_name.setText(portfolio.name)
        for btn in (self.btn_buy, self.btn_sell, self.btn_refresh):
            btn.setEnabled(True)
        self._update_view()

    def _update_view(self):
        if self.current_portfolio_id is None:
            return
        summary = self.model_portfolio_service.get_portfolio_summary(
            self.current_portfolio_id, self.current_price_map
        )

        self.card_initial.set_value(f"₺ {summary['initial_cash']:,.2f}")
        self.card_cash.set_value(f"₺ {summary['remaining_cash']:,.2f}")
        self.card_value.set_value(f"₺ {summary['total_value']:,.2f}")

        pl = summary["profit_loss"]
        self.card_pl.set_value(f"₺ {pl:+,.2f}")
        self.card_pl.set_value_state("positive" if pl >= 0 else "negative")

        positions = self.model_portfolio_service.get_positions_with_details(
            self.current_portfolio_id, self.current_price_map
        )
        self.positions_table.populate(positions)

    def _clear_right_panel(self):
        self.lbl_portfolio_name.setText("Bir portföy seçin")
        self.positions_table.setRowCount(0)
        for btn in (self.btn_buy, self.btn_sell, self.btn_refresh):
            btn.setEnabled(False)
        for card in (self.card_initial, self.card_cash, self.card_value, self.card_pl):
            card.set_value("₺ 0")
            card.set_value_state("neutral")

    # ------------------------------------------------------------------
    # CRUD İşlemleri
    # ------------------------------------------------------------------

    def _on_new_portfolio(self):
        dialog = PortfolioInputDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        result = dialog.get_result()
        if not result:
            return
        try:
            self.model_portfolio_service.create_portfolio(**result)
            self._load_portfolios()
            Toast.success(self, f"'{result['name']}' portföyü oluşturuldu.")
        except Exception as e:
            Toast.error(self, f"Portföy oluşturulamadı: {e}")

    def _on_edit_portfolio(self):
        if self.current_portfolio_id is None:
            return
        portfolio = self.list_panel.current_portfolio()
        if not portfolio:
            return
        dialog = PortfolioInputDialog(self, portfolio)
        if dialog.exec_() != QDialog.Accepted:
            return
        result = dialog.get_result()
        if not result:
            return
        try:
            self.model_portfolio_service.update_portfolio(
                portfolio_id=self.current_portfolio_id, **result
            )
            self._load_portfolios()
            self.lbl_portfolio_name.setText(result["name"])
            self._update_view()
            Toast.success(self, "Portföy güncellendi.")
        except Exception as e:
            Toast.error(self, f"Portföy güncellenemedi: {e}")

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
            Toast.success(self, "Portföy silindi.")
        except Exception as e:
            Toast.error(self, f"Portföy silinemedi: {e}")

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
            Toast.success(self, f"{result['quantity']} lot {result['ticker']} {action}.")
        except ValueError as e:
            Toast.warning(self, str(e))
        except Exception as e:
            Toast.error(self, f"İşlem gerçekleştirilemedi: {e}")

    def _on_refresh_prices(self):
        if self.current_portfolio_id is None:
            return
        if not self.price_lookup_func:
            Toast.warning(self, "Fiyat sorgulama fonksiyonu mevcut değil.")
            return
        positions = self.model_portfolio_service.get_positions_with_details(self.current_portfolio_id)
        updated_count = 0
        for pos in positions:
            try:
                result = self.price_lookup_func(pos["ticker"])
                if result:
                    self.current_price_map[pos["stock_id"]] = result.price
                    updated_count += 1
            except Exception as e:
                logger.error(f"Fiyat alınamadı: {pos['ticker']} - {e}")
        self._update_view()
        Toast.success(self, f"{updated_count} hisse için fiyat güncellendi.")


# ======================================================================
#  Diyaloglar (sayfa dosyasında kalabilir; küçük ve bağımlı diyaloglar)
# ======================================================================

class PortfolioInputDialog(QDialog):
    """Portföy oluşturma / düzenleme diyaloğu."""

    def __init__(self, parent=None, portfolio: Optional[ModelPortfolio] = None):
        super().__init__(parent)
        self.portfolio = portfolio
        self.is_edit = portfolio is not None
        self.setWindowTitle("Portföy Düzenle" if self.is_edit else "Yeni Portföy")
        self.resize(400, 200)
        self.setModal(True)
        self.setProperty("cssClass", "tradeDialog")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_name = QLineEdit(self.portfolio.name if self.is_edit else "")
        form.addRow("Adı:", self.txt_name)

        self.txt_desc = QLineEdit(
            (self.portfolio.description or "") if self.is_edit else ""
        )
        form.addRow("Açıklama:", self.txt_desc)

        self.spin_cash = QDoubleSpinBox()
        self.spin_cash.setRange(1000, 100_000_000)
        self.spin_cash.setDecimals(2)
        self.spin_cash.setSuffix(" TL")
        self.spin_cash.setValue(float(self.portfolio.initial_cash) if self.is_edit else 100_000)
        form.addRow("Sermaye:", self.spin_cash)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setProperty("cssClass", "secondaryButton")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Kaydet")
        btn_save.setProperty("cssClass", "successButton")
        btn_save.clicked.connect(self.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    def get_result(self) -> Optional[dict]:
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
        self.setFixedSize(450, 320)
        self.setModal(True)
        self.setProperty("cssClass", "tradeDialog")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        form = QFormLayout()
        form.setSpacing(15)
        form.setLabelAlignment(Qt.AlignLeft)

        self.txt_ticker = QLineEdit()
        self.txt_ticker.setPlaceholderText("Örn: ASELS")
        self.txt_ticker.setMinimumHeight(45)
        self.txt_ticker.returnPressed.connect(self._on_lookup)
        form.addRow("Ticker:", self.txt_ticker)

        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 1_000_000)
        self.spin_qty.setValue(100)
        self.spin_qty.setMinimumHeight(45)
        form.addRow("Lot:", self.spin_qty)

        price_row = QHBoxLayout()
        self.spin_price = QDoubleSpinBox()
        self.spin_price.setRange(0.01, 100_000)
        self.spin_price.setDecimals(2)
        self.spin_price.setSuffix(" TL")
        self.spin_price.setMinimumWidth(180)
        self.spin_price.setMinimumHeight(45)
        price_row.addWidget(self.spin_price)

        btn_lookup = QPushButton("🔍 Fiyat Al")
        btn_lookup.setCursor(Qt.PointingHandCursor)
        btn_lookup.setProperty("cssClass", "primaryButton")
        btn_lookup.setMinimumHeight(45)
        btn_lookup.clicked.connect(self._on_lookup)
        price_row.addWidget(btn_lookup)
        form.addRow("Fiyat:", price_row)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setMinimumHeight(45)
        form.addRow("Tarih:", self.date_edit)

        layout.addLayout(form)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setMinimumHeight(40)
        btn_cancel.setProperty("cssClass", "secondaryButton")
        btn_cancel.clicked.connect(self.reject)

        btn_action = QPushButton("Al" if self.side == "BUY" else "Sat")
        btn_action.setMinimumHeight(40)
        btn_action.setProperty("cssClass", "successButton" if self.side == "BUY" else "dangerButton")
        btn_action.clicked.connect(self.accept)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_action)
        layout.addLayout(btn_row)

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
        except Exception as e:
            logger.warning(f"Fiyat sorgulama başarısız ({ticker}): {e}")

    def get_result(self) -> Optional[dict]:
        ticker = self.txt_ticker.text().strip()
        if not ticker:
            return None
        return {
            "ticker": ticker.upper(),
            "quantity": self.spin_qty.value(),
            "price": Decimal(str(self.spin_price.value())),
            "trade_date": self.date_edit.date().toPyDate(),
        }

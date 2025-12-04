# src/ui/main_window.py

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, List

from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTableView,
    QMessageBox,
)
from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtWidgets import QDialog

from src.ui.widgets.new_stock_trade_dialog import NewStockTradeDialog
from src.domain.models.trade import Trade, TradeSide
from src.domain.models.stock import Stock
from src.domain.services_interfaces.i_stock_repo import IStockRepository  # sadece type hint istersen
from src.ui.widgets.trade_dialog import TradeDialog
from src.application.services.portfolio_service import PortfolioService
from src.application.services.return_calc_service import ReturnCalcService
from src.application.services.portfolio_update_coordinator import PortfolioUpdateCoordinator
from src.ui.portfolio_table_model import PortfolioTableModel
from src.domain.models.position import Position
from src.domain.models.portfolio import Portfolio


class MainWindow(QMainWindow):
    def __init__(
        self,
        portfolio_service: PortfolioService,
        return_calc_service: ReturnCalcService,
        update_coordinator: PortfolioUpdateCoordinator,
        stock_repo,   # <--- yeni parametre
        parent=None,
    ):
        super().__init__(parent)
        self.portfolio_service = portfolio_service
        self.return_calc_service = return_calc_service
        self.update_coordinator = update_coordinator
        self.stock_repo = stock_repo   # <--- sakla

        self.setWindowTitle("Portföy Simülasyonu")
        self.resize(1000, 600)

        self._init_ui()
        self._load_initial_data()

    # --------- UI Kurulumu --------- #

    def _init_ui(self):
        central = QWidget()
        main_layout = QVBoxLayout(central)

        # Üstte butonlar
        button_layout = QHBoxLayout()
        self.btn_new_trade = QPushButton("Yeni Hisse / İşlem Ekle")   # YENİ
        self.btn_update_prices = QPushButton("Gün Sonu Fiyatlarını Güncelle")
        self.btn_refresh_returns = QPushButton("Haftalık / Aylık Getiriyi Göster")

        button_layout.addWidget(self.btn_new_trade)
        button_layout.addWidget(self.btn_update_prices)
        button_layout.addWidget(self.btn_refresh_returns)
        button_layout.addStretch()

        # Orta: tablo
        self.table_view = QTableView()

        # Alt: özet label'ları
        summary_layout = QHBoxLayout()
        self.lbl_total_value = QLabel("Toplam Değer: -")
        self.lbl_weekly_return = QLabel("Haftalık Getiri: -")
        self.lbl_monthly_return = QLabel("Aylık Getiri: -")

        for lbl in (self.lbl_total_value, self.lbl_weekly_return, self.lbl_monthly_return):
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            summary_layout.addWidget(lbl)

        summary_layout.addStretch()

        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.table_view)
        main_layout.addLayout(summary_layout)

        self.setCentralWidget(central)

        # Signal/slot bağlantıları
        self.btn_update_prices.clicked.connect(self.on_update_prices_clicked)
        self.btn_refresh_returns.clicked.connect(self.on_refresh_returns_clicked)
        self.btn_new_trade.clicked.connect(self.on_new_stock_trade_clicked)
        self.btn_update_prices.clicked.connect(self.on_update_prices_clicked)
        self.btn_refresh_returns.clicked.connect(self.on_refresh_returns_clicked)


    # --------- Başlangıç verisi yükleme --------- #

    def _load_initial_data(self):
        """
        Uygulama açıldığında mevcut trade'lerden portföyü hesaplar
        ve tabloyu doldurur.
        """
        # Tüm trade'leri al → Portfolio
        portfolio: Portfolio = self.portfolio_service.get_current_portfolio()

        # Bugünün yerine istersen son fiyatın olduğu tarihi kullanabilirsin,
        # şimdilik bugün diyelim:
        today = date.today()
        _, end_snapshot = self._get_single_day_snapshot(today)

        # Pozisyon listesi:
        positions: List[Position] = list(portfolio.positions.values())
        price_map: Dict[int, Decimal] = end_snapshot.price_map if end_snapshot else {}

        self.model = PortfolioTableModel(positions, price_map, parent=self)
        self.table_view.setModel(self.model)

        # Özet label'ları güncelle
        if end_snapshot:
            self.lbl_total_value.setText(f"Toplam Değer: {end_snapshot.total_value:.2f}")
        
        self.table_view.doubleClicked.connect(self.on_table_double_clicked)


    # --------- Yardımcı: tek gün snapshot (bugün veya herhangi bir tarih) --------- #

    def _get_single_day_snapshot(self, value_date: date):
        """
        ReturnCalcService ile value_date için snapshot hesaplar.
        Küçük bir helper.
        """
        snapshot = self.return_calc_service.compute_portfolio_value_on(value_date)
        return value_date, snapshot

    # --------- Slot: Gün sonu fiyatlarını güncelle --------- #

    def on_update_prices_clicked(self):
        try:
            price_update_result, snapshot = self.update_coordinator.update_today_prices_and_get_snapshot()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Fiyat güncelleme sırasında hata: {e}")
            return

        # Tabloyu güncellemek için:
        portfolio: Portfolio = self.portfolio_service.get_current_portfolio()
        positions: List[Position] = list(portfolio.positions.values())
        price_map = snapshot.price_map

        if hasattr(self, "model"):
            self.model.update_data(positions, price_map)
        else:
            self.model = PortfolioTableModel(positions, price_map, parent=self)
            self.table_view.setModel(self.model)

        # Özet label'ları
        self.lbl_total_value.setText(f"Toplam Değer: {snapshot.total_value:.2f}")

        QMessageBox.information(
            self,
            "Güncelleme Tamamlandı",
            f"{price_update_result.updated_count} hisse için gün sonu fiyatı güncellendi.",
        )

    # --------- Slot: Haftalık / aylık getiri --------- #

    def on_refresh_returns_clicked(self):
        today = date.today()
        try:
            weekly_rate, _, _ = self.return_calc_service.compute_weekly_return(today)
            monthly_rate, _, _ = self.return_calc_service.compute_monthly_return(today)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Getiri hesaplama sırasında hata: {e}")
            return

        if weekly_rate is not None:
            self.lbl_weekly_return.setText(f"Haftalık Getiri: %{(weekly_rate * 100):.2f}")
        else:
            self.lbl_weekly_return.setText("Haftalık Getiri: -")

        if monthly_rate is not None:
            self.lbl_monthly_return.setText(f"Aylık Getiri: %{(monthly_rate * 100):.2f}")
        else:
            self.lbl_monthly_return.setText("Aylık Getiri: -")

    def on_table_double_clicked(self, index: QModelIndex):
        """
        Kullanıcı tablo satırına çift tıkladığında yeni işlem eklemek için dialog açar.
        """
        if not index.isValid():
            return

        row = index.row()
        # Modelden pozisyonu al
        position: Position = self.model.get_position(row)
        stock_id = position.stock_id

        # Şimdilik ticker'ı bilmiyoruz; istersen stock_repo ile lookup yapıp verebilirsin.
        dialog = TradeDialog(stock_id=stock_id, ticker=None, parent=self)

        if dialog.exec_() != QDialog.Accepted:
            return

        trade_data = dialog.get_trade_data()
        if not trade_data:
            return

        # Trade domain objesini oluştur
        if trade_data["side"] == "BUY":
            trade = Trade.create_buy(
                stock_id=trade_data["stock_id"],
                trade_date=trade_data["trade_date"],
                quantity=trade_data["quantity"],
                price=trade_data["price"],
                trade_time=trade_data["trade_time"],
            )
        else:
            trade = Trade.create_sell(
                stock_id=trade_data["stock_id"],
                trade_date=trade_data["trade_date"],
                quantity=trade_data["quantity"],
                price=trade_data["price"],
                trade_time=trade_data["trade_time"],
            )

        # Service çağrısı: DB'ye kaydet
        try:
            self.portfolio_service.add_trade(trade)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"İşlem kaydedilemedi: {e}")
            return

        # Tablo ve özetleri yenile (basit çözüm: baştan yükle)
        self._load_initial_data()

    def on_new_stock_trade_clicked(self):
        """
        Üstteki 'Yeni Hisse / İşlem Ekle' butonunun handler'ı.
        Yeni hisse gerekiyorsa ekler, ardından trade'i kaydeder, tabloyu yeniler.
        """
        dlg = NewStockTradeDialog(parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return

        data = dlg.get_result()
        if not data:
            return

        ticker = data["ticker"]
        name = data["name"]

        # 1) Hisse zaten var mı?
        try:
            existing_stock = self.stock_repo.get_stock_by_ticker(ticker)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Hisse sorgulanırken hata: {e}")
            return

        if existing_stock is None:
            # Yeni hisse oluştur
            try:
                new_stock = Stock(id=None, ticker=ticker, name=name or ticker, currency_code="TRY")
                saved_stock = self.stock_repo.insert_stock(new_stock)
                stock_id = saved_stock.id
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Yeni hisse eklenemedi: {e}")
                return
        else:
            stock_id = existing_stock.id

        # 2) Trade domain objesi oluştur
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
        except ValueError as e:
            QMessageBox.warning(self, "Geçersiz İşlem", str(e))
            return

        # 3) Trade'i kaydet
        try:
            self.portfolio_service.add_trade(trade)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"İşlem kaydedilemedi: {e}")
            return

        # 4) Ekranı yenile
        self._load_initial_data()
        QMessageBox.information(self, "Başarılı", "İşlem başarıyla eklendi.")

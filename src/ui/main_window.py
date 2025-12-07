# src/ui/main_window.py

from __future__ import annotations

import yfinance as yf
from datetime import datetime, timezone
from datetime import date
from decimal import Decimal
from typing import Dict, List,NamedTuple, Optional

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
from PyQt5.QtWidgets import QDialog,QHeaderView

from src.ui.widgets.trade_dialog import TradeDialog
from src.ui.widgets.new_stock_trade_dialog import NewStockTradeDialog
from src.ui.portfolio_table_model import PortfolioTableModel
from src.ui.widgets.edit_stock_dialog import EditStockDialog

from src.domain.models.stock import Stock
from src.domain.models.trade import Trade, TradeSide
from src.domain.models.stock import Stock
from src.domain.services_interfaces.i_stock_repo import IStockRepository  # sadece type hint istersen
from src.domain.models.position import Position
from src.domain.models.portfolio import Portfolio

from src.application.services.portfolio_service import PortfolioService
from src.application.services.return_calc_service import ReturnCalcService
from src.application.services.portfolio_update_coordinator import PortfolioUpdateCoordinator

class PriceLookupResult(NamedTuple):
    price: Decimal
    as_of: datetime    # fiyatın zamanı
    source: str        # "intraday" veya "last_close"


class MainWindow(QMainWindow):
    def __init__(
        self,
        portfolio_service: PortfolioService,
        return_calc_service: ReturnCalcService,
        update_coordinator: PortfolioUpdateCoordinator,
        stock_repo,   # <--- yeni parametre
        reset_service,
        market_client,
        parent=None,
    ):
        super().__init__(parent)
        self.portfolio_service = portfolio_service
        self.return_calc_service = return_calc_service
        self.update_coordinator = update_coordinator
        self.stock_repo = stock_repo   # <--- sakla
        self.reset_service = reset_service   # <--- sakla
        self.market_client = market_client   # <--- sakla

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
        self.btn_reset_portfolio = QPushButton("Portföyü Sıfırla")   # <--- YENİ
        self.btn_update_prices.setObjectName("primaryButton")

        button_layout.addWidget(self.btn_new_trade)
        button_layout.addWidget(self.btn_update_prices)
        button_layout.addWidget(self.btn_refresh_returns)
        button_layout.addWidget(self.btn_reset_portfolio)   # <--- YENİ
        button_layout.addStretch()

        # Orta: tablo
        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setSortingEnabled(True)
        self.table_view.verticalHeader().setVisible(False)

        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setHighlightSections(False)

        self.table_view.setStyleSheet("QTableView { border-radius: 8px; }")
        self.table_view.setShowGrid(True)

        # Alt: özet label'ları
        summary_layout = QHBoxLayout()

        def make_summary_label(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setObjectName("summaryLabel")
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            return lbl

        self.lbl_total_value = make_summary_label("Toplam Değer: 0.00")
        self.lbl_weekly_return = make_summary_label("Haftalık Getiri: -")
        self.lbl_monthly_return = make_summary_label("Aylık Getiri: -")

        summary_layout.addWidget(self.lbl_total_value)
        summary_layout.addSpacing(24)
        summary_layout.addWidget(self.lbl_weekly_return)
        summary_layout.addSpacing(24)
        summary_layout.addWidget(self.lbl_monthly_return)
        summary_layout.addStretch()
        
        # Layout ekleme
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
        self.btn_reset_portfolio.clicked.connect(self.on_reset_portfolio_clicked)  # <--- YENİ


    # --------- Başlangıç verisi yükleme --------- #

    def _load_initial_data(self):
        portfolio: Portfolio = self.portfolio_service.get_current_portfolio()

        today = date.today()
        _, end_snapshot = self._get_single_day_snapshot(today)

        all_positions: List[Position] = list(portfolio.positions.values())
        positions: List[Position] = [
            p for p in all_positions
            if p.total_quantity != 0
        ]

        price_map: Dict[int, Decimal] = end_snapshot.price_map if end_snapshot else {}

        # Ticker map: { stock_id: "AKBNK.IS", ... }
        stock_ids = [p.stock_id for p in positions]
        ticker_map = self.stock_repo.get_ticker_map_for_stock_ids(stock_ids)

        self.model = PortfolioTableModel(positions, price_map, ticker_map, parent=self)
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
        all_positions: List[Position] = list(portfolio.positions.values())
        positions: List[Position] = [
            p for p in all_positions
            if p.total_quantity != 0
        ]

        price_map = snapshot.price_map

        stock_ids = [p.stock_id for p in positions]
        ticker_map = self.stock_repo.get_ticker_map_for_stock_ids(stock_ids)

        if hasattr(self, "model"):
            self.model.update_data(positions, price_map, ticker_map)
        else:
            self.model = PortfolioTableModel(positions, price_map, ticker_map, parent=self)
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
        Kullanıcı tablo satırına çift tıklayınca:
          - Varsayılan: yeni trade ekleme
          - İsterse: 'Hisseyi Düzenle' butonuyla ticker/ad düzenleme
        """
        if not index.isValid():
            return

        if not hasattr(self, "model") or self.model is None:
            return

        row = index.row()
        if row < 0 or row >= self.model.rowCount():
            return

        position: Position = self.model.get_position(row)
        stock_id = position.stock_id

        # Mevcut ticker'ı repo'dan alalım (label için de kullanabiliriz)
        stock = self.stock_repo.get_stock_by_id(stock_id)
        ticker = stock.ticker if stock is not None else None

        dialog = TradeDialog(
            stock_id=stock_id,
            ticker=ticker,
            parent=self,
            price_lookup_func=self.lookup_price_for_ticker,  # yeni
            lot_size=1,                                      # istersen 100
        )


        if dialog.exec_() != QDialog.Accepted:
            return

        # 1) Hisseyi düzenleme modu
        if dialog.get_mode() == "edit_stock":
            if stock is None:
                QMessageBox.warning(self, "Uyarı", "Bu pozisyona ait hisse kaydı bulunamadı.")
                return

            edit_dlg = EditStockDialog(stock, parent=self)
            if edit_dlg.exec_() != QDialog.Accepted:
                return

            try:
                result = edit_dlg.get_result()
            except ValueError as e:
                QMessageBox.warning(self, "Geçersiz Girdi", str(e))
                return

            updated_stock = Stock(
                id=stock.id,
                ticker=result.ticker,
                name=result.name,
                currency_code=stock.currency_code,
                created_at=stock.created_at,
                updated_at=stock.updated_at,
            )

            try:
                self.stock_repo.update_stock(updated_stock)
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Hisse güncellenemedi:\n{e}")
                return

            self._load_initial_data()
            QMessageBox.information(self, "Başarılı", "Hisse bilgileri güncellendi.")
            return

        # 2) Normal trade modu
        trade_data = dialog.get_trade_data()
        if not trade_data:
            return

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

        try:
            self.portfolio_service.add_trade(trade)
        except ValueError as e:
            msg = str(e)
            if "Cannot sell more than current position quantity" in msg:
                QMessageBox.warning(
                    self,
                    "Geçersiz İşlem",
                    "Elindeki lottan fazla satış yapamazsın.\n"
                    "Önce yeterli alış işlemi eklemelisin.",
                )
            else:
                QMessageBox.warning(self, "Geçersiz İşlem", msg)
            return
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"İşlem kaydedilemedi: {e}")
            return

        self._load_initial_data()


    def on_new_stock_trade_clicked(self):
        """
        Üstteki 'Yeni Hisse / İşlem Ekle' butonunun handler'ı.
        Yeni hisse gerekiyorsa ekler, ardından trade'i kaydeder, tabloyu yeniler.
        """
        dlg = NewStockTradeDialog(
            parent=self,
            price_lookup_func=self.lookup_price_for_ticker,
            lot_size=1,  # ya da 100, nasıl tanımlamak istiyorsan
        )
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
        except ValueError as e:
            msg = str(e)
            if "Cannot sell more than current position quantity" in msg:
                QMessageBox.warning(
                    self,
                    "Geçersiz İşlem",
                    "Elinde o kadar lot yok, daha fazla satamazsın.\n"
                    "Önce yeterli alış işlemi eklemen gerekiyor.",
                )
            else:
                QMessageBox.warning(self, "Geçersiz İşlem", msg)
            return
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"İşlem kaydedilemedi: {e}")
            return

        # 4) Ekranı yenile
        self._load_initial_data()
        QMessageBox.information(self, "Başarılı", "İşlem başarıyla eklendi.")

    def on_reset_portfolio_clicked(self):
        """
        'Portföyü Sıfırla' butonu:
        Tüm hisseleri, işlemleri ve fiyat kayıtlarını siler.
        """
        reply = QMessageBox.question(
            self,
            "Portföyü Sıfırla",
            "TÜM hisse, işlem ve fiyat kayıtları silinecek.\n"
            "Bu işlem geri alınamaz. Emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        try:
            self.reset_service.reset_all()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Portföy sıfırlanırken hata oluştu:\n{e}")
            return

        # UI'ı sıfırla
        self._load_initial_data()
        self.lbl_total_value.setText("Toplam Değer: 0.00")
        self.lbl_weekly_return.setText("Haftalık Getiri: -")
        self.lbl_monthly_return.setText("Aylık Getiri: -")

        QMessageBox.information(self, "Tamamlandı", "Portföy başarıyla sıfırlandı.")

    def lookup_price_for_ticker(self, ticker: str) -> Optional[PriceLookupResult]:
        """
        UI dialog'larının kullanacağı gelişmiş fiyat lookup.

        Öncelik sırası:
          1) intraday (current/regularMarketPrice)
          2) son işlem gününün kapanış fiyatı (history)

        Hata veya veri yoksa None döner.
        """
        if not ticker:
            return None

        # BIST için .IS ekleyelim (yoksa)
        if "." not in ticker:
            ticker = ticker.upper() + ".IS"
        else:
            ticker = ticker.upper()

        try:
            yt = yf.Ticker(ticker)
        except Exception as e:
            print("YF Ticker init failed:", e)
            return None

        # 1) Intraday denemesi
        price = None
        info = {}
        try:
            # fast_info daha hızlı, yoksa info
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

        # 2) Fallback: son kapanış (last close)
        try:
            hist = yt.history(period="5d", auto_adjust=False)
        except Exception as e:
            print("YF history failed for", ticker, ":", e)
            return None

        if hist is not None and not hist.empty and "Close" in hist:
            # Close sütunu dolu son satır
            close_series = hist["Close"].dropna()
            if not close_series.empty:
                last_ts = close_series.index[-1]
                last_price = close_series.iloc[-1]
                try:
                    price = Decimal(str(float(last_price)))
                    # index genelde Timestamp
                    if hasattr(last_ts, "to_pydatetime"):
                        as_of = last_ts.to_pydatetime().replace(tzinfo=timezone.utc)
                    else:
                        as_of = datetime.now(timezone.utc)
                    return PriceLookupResult(price=price, as_of=as_of, source="last_close")
                except Exception:
                    pass

        print("Price lookup failed for", ticker)
        return None

   
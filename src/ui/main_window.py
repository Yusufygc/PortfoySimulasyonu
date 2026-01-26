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
    QFrame
)
from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtWidgets import QDialog,QHeaderView,QFileDialog

from src.ui.widgets.date_range_dialog import DateRangeDialog
from src.ui.widgets.trade_dialog import TradeDialog
from src.ui.widgets.new_stock_trade_dialog import NewStockTradeDialog
from src.ui.portfolio_table_model import PortfolioTableModel
from src.ui.widgets.edit_stock_dialog import EditStockDialog
from src.ui.widgets.watchlist_manager_dialog import WatchlistManagerDialog

from src.domain.models.stock import Stock
from src.domain.models.trade import Trade, TradeSide
from src.domain.models.position import Position
from src.domain.models.portfolio import Portfolio

from src.application.services.portfolio_service import PortfolioService
from src.application.services.return_calc_service import ReturnCalcService
from src.application.services.portfolio_update_coordinator import PortfolioUpdateCoordinator
from src.application.services.excel_export_service import ExcelExportService, ExportMode

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
        excel_export_service: ExcelExportService,
        stock_repo,
        reset_service,
        market_client,
        watchlist_service=None,
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
        
        self.setWindowTitle("Portföy Simülasyonu")
        self.resize(1000, 600)

        self._init_ui()
        self._load_initial_data()

    # --------- UI Kurulumu --------- #

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
        self.sidebar.setFixedWidth(250)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(15, 25, 15, 25)
        self.sidebar_layout.setSpacing(15)

        # Butonlar
        self.btn_new_trade = QPushButton("Yeni İşlem Ekle")
        self.btn_new_trade.setObjectName("primaryButton")
        self.btn_new_trade.setCursor(Qt.PointingHandCursor)

        self.btn_update_prices = QPushButton("Fiyatları Güncelle")
        self.btn_update_prices.setCursor(Qt.PointingHandCursor)

        self.btn_refresh_returns = QPushButton("Getiri Analizi")
        self.btn_refresh_returns.setCursor(Qt.PointingHandCursor)

        self.btn_export_today = QPushButton("Rapor: Bugün")
        self.btn_export_today.setCursor(Qt.PointingHandCursor)

        self.btn_export_range = QPushButton("Rapor: Tarih Aralığı")
        self.btn_export_range.setCursor(Qt.PointingHandCursor)
        
        self.btn_watchlists = QPushButton("📋 Listelerim")
        self.btn_watchlists.setCursor(Qt.PointingHandCursor)

        self.btn_reset_portfolio = QPushButton("Sistemi Sıfırla")
        self.btn_reset_portfolio.setStyleSheet("color: #ef4444;")
        self.btn_reset_portfolio.setCursor(Qt.PointingHandCursor)

        # Sidebar'a ekle
        self.sidebar_layout.addWidget(self.btn_new_trade)
        self.sidebar_layout.addWidget(self.btn_update_prices)
        self.sidebar_layout.addWidget(self.btn_refresh_returns)
        
        # Ayraç
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #334155;")
        self.sidebar_layout.addWidget(line)
        
        # Rapor butonlarını ekle (Checkbox kaldırıldı)
        self.sidebar_layout.addWidget(self.btn_export_today)
        self.sidebar_layout.addWidget(self.btn_export_range)
        
        # Ayraç 2
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("background-color: #334155;")
        self.sidebar_layout.addWidget(line2)
        
        # Listelerim butonu
        self.sidebar_layout.addWidget(self.btn_watchlists)
        self.sidebar_layout.addStretch()
        self.sidebar_layout.addWidget(self.btn_reset_portfolio)

        # --- 2. SAĞ İÇERİK ALANI ---
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(25, 25, 25, 25)
        self.content_layout.setSpacing(20)

        # A) Dashboard Kartları (Üst Kısım)
        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(20)

        def create_card(title, initial_value):
            card = QFrame()
            card.setObjectName("infoCard")
            card.setFrameShape(QFrame.StyledPanel)
            
            l_layout = QVBoxLayout(card)
            l_layout.setContentsMargins(20, 20, 20, 20)
            
            lbl_title = QLabel(title)
            lbl_title.setObjectName("cardTitle")
            
            lbl_value = QLabel(initial_value)
            lbl_value.setObjectName("cardValue")
            
            l_layout.addWidget(lbl_title)
            l_layout.addWidget(lbl_value)
            return card, lbl_value

        self.card_total, self.lbl_total_value = create_card("TOPLAM PORTFÖY DEĞERİ", "₺ 0.00")
        self.card_weekly, self.lbl_weekly_return = create_card("HAFTALIK GETİRİ", "-")
        self.card_monthly, self.lbl_monthly_return = create_card("AYLIK GETİRİ", "-")

        self.cards_layout.addWidget(self.card_total)
        self.cards_layout.addWidget(self.card_weekly)
        self.cards_layout.addWidget(self.card_monthly)

        # B) Tablo (Orta Kısım)
        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(False)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setSortingEnabled(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.setShowGrid(False)

        self.content_layout.addLayout(self.cards_layout)
        self.content_layout.addWidget(self.table_view)

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.content_area)

        # Signal/Slot Bağlantıları
        self.btn_update_prices.clicked.connect(self.on_update_prices_clicked)
        self.btn_refresh_returns.clicked.connect(self.on_refresh_returns_clicked)
        self.btn_new_trade.clicked.connect(self.on_new_stock_trade_clicked)
        self.btn_export_range.clicked.connect(self.on_export_range_clicked)
        self.btn_export_today.clicked.connect(self.on_export_today_clicked)
        self.btn_reset_portfolio.clicked.connect(self.on_reset_portfolio_clicked)
        self.btn_watchlists.clicked.connect(self.on_watchlists_clicked)


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

        stock_ids = [p.stock_id for p in positions]
        ticker_map = self.stock_repo.get_ticker_map_for_stock_ids(stock_ids)

        self.model = PortfolioTableModel(positions, price_map, ticker_map, parent=self)
        self.table_view.setModel(self.model)

        if end_snapshot:
            self.lbl_total_value.setText(f"₺ {end_snapshot.total_value:,.2f}")
        
        self.table_view.doubleClicked.connect(self.on_table_double_clicked)


    def _get_single_day_snapshot(self, value_date: date):
        snapshot = self.return_calc_service.compute_portfolio_value_on(value_date)
        return value_date, snapshot

    def on_update_prices_clicked(self):
        try:
            price_update_result, snapshot = self.update_coordinator.update_today_prices_and_get_snapshot()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Fiyat güncelleme sırasında hata: {e}")
            return

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

        self.lbl_total_value.setText(f"Toplam Değer: {snapshot.total_value:.2f}")

        QMessageBox.information(
            self,
            "Güncelleme Tamamlandı",
            f"{price_update_result.updated_count} hisse için gün sonu fiyatı güncellendi.",
        )

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
        if not index.isValid():
            return

        if not hasattr(self, "model") or self.model is None:
            return

        row = index.row()
        if row < 0 or row >= self.model.rowCount():
            return

        position: Position = self.model.get_position(row)
        stock_id = position.stock_id

        stock = self.stock_repo.get_stock_by_id(stock_id)
        ticker = stock.ticker if stock is not None else None

        dialog = TradeDialog(
            stock_id=stock_id,
            ticker=ticker,
            parent=self,
            price_lookup_func=self.lookup_price_for_ticker,
            lot_size=1,
        )

        if dialog.exec_() != QDialog.Accepted:
            return

        # Hisseyi düzenleme modu
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

        # Normal trade modu
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
        dlg = NewStockTradeDialog(
            parent=self,
            price_lookup_func=self.lookup_price_for_ticker,
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
        except ValueError as e:
            QMessageBox.warning(self, "Geçersiz İşlem", str(e))
            return

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

        self._load_initial_data()
        QMessageBox.information(self, "Başarılı", "İşlem başarıyla eklendi.")

    def on_reset_portfolio_clicked(self):
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

        self._load_initial_data()
        self.lbl_total_value.setText("Toplam Değer: 0.00")
        self.lbl_weekly_return.setText("Haftalık Getiri: -")
        self.lbl_monthly_return.setText("Aylık Getiri: -")

        QMessageBox.information(self, "Tamamlandı", "Portföy başarıyla sıfırlandı.")

    def on_watchlists_clicked(self):
        """Watchlist yönetimi diyaloğunu açar."""
        if self.watchlist_service is None:
            QMessageBox.warning(
                self,
                "Uyarı",
                "Watchlist servisi yüklenmedi. Lütfen uygulamayı yeniden başlatın."
            )
            return

        dialog = WatchlistManagerDialog(
            watchlist_service=self.watchlist_service,
            price_lookup_func=self.lookup_price_for_ticker,
            parent=self,
        )
        dialog.exec_()

    def lookup_price_for_ticker(self, ticker: str) -> Optional[PriceLookupResult]:
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

    def _get_first_trade_date(self) -> Optional[date]:
        trades = self.portfolio_service._portfolio_repo.get_all_trades()
        if not trades:
            return None
        return min(t.trade_date for t in trades)

    def on_export_range_clicked(self):
        first_date = self._get_first_trade_date()
        if first_date is None:
            QMessageBox.information(self, "Bilgi", "Herhangi bir işlem bulunamadı; aktarılacak veri yok.")
            return

        today = date.today()

        dlg = DateRangeDialog(self, min_date=first_date, max_date=today)
        if dlg.exec_() != QDialog.Accepted:
            return

        result = dlg.get_range()
        if not result:
            return
        start_date, end_date = result

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Excel Dosyası Seç",
            "portfoy_takip.xlsx",
            "Excel Dosyaları (*.xlsx)",
        )
        if not file_path:
            return

        choice = QMessageBox.question(
            self,
            "Yazma Modu",
            "Var olan dosyanın üzerine yazmak ister misiniz?\n"
            "Evet: dosya baştan oluşturulur\n"
            "Hayır: var olan dosyaya ekleme yapılır",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if choice == QMessageBox.Cancel:
            return

        mode = ExportMode.OVERWRITE if choice == QMessageBox.Yes else ExportMode.APPEND

        try:
            self.excel_export_service.export_history(
                start_date=start_date,
                end_date=end_date,
                file_path=file_path,
                mode=mode,
            )
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Excel aktarımı sırasında hata oluştu:\n{e}")
            return

        QMessageBox.information(self, "Başarılı", "Excel aktarımı tamamlandı.")


    def on_export_today_clicked(self):
        first_date = self._get_first_trade_date()
        if first_date is None:
            QMessageBox.information(self, "Bilgi", "Herhangi bir işlem bulunamadı; aktarılacak veri yok.")
            return

        today = date.today()

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Excel Dosyası Seç",
            "portfoy_takip.xlsx",
            "Excel Dosyaları (*.xlsx)",
        )
        if not file_path:
            return

        choice = QMessageBox.question(
            self,
            "Yazma Modu",
            "Var olan dosyanın üzerine yazmak ister misiniz?\n"
            "Evet: dosya baştan oluşturulur\n"
            "Hayır: var olan dosyaya ekleme yapılır",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if choice == QMessageBox.Cancel:
            return

        mode = ExportMode.OVERWRITE if choice == QMessageBox.Yes else ExportMode.APPEND

        try:
            self.excel_export_service.export_history(
                start_date=first_date,
                end_date=today,
                file_path=file_path,
                mode=mode,
            )
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Excel aktarımı sırasında hata oluştu:\n{e}")
            return

        QMessageBox.information(self, "Başarılı", "Excel aktarımı tamamlandı.")
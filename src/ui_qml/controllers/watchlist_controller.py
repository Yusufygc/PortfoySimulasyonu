"""
Watchlist Controller — Takip listeleri (Watchlist) yönetimi, çoklu liste sekmeleri,
anlık fiyat değişimleri ve 7 günlük mini sparkline verilerini sağlar.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional

from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer
from src.domain.ticker import clean_ticker
from src.ui_qml.models.watchlist_table_model import WatchlistTableModel

logger = logging.getLogger(__name__)


class WatchlistController(QObject):
    watchlistsChanged = Signal()
    currentWatchlistChanged = Signal()
    stocksChanged = Signal()
    refreshStateChanged = Signal(bool)
    actionCompleted = Signal(bool, str)  # success, message

    def __init__(self, container=None, parent=None):
        super().__init__(parent)
        self._container = container
        self._stocks_model = WatchlistTableModel(self)

        self._watchlists: List[Dict[str, Any]] = []
        self._current_watchlist_id: int = -1
        self._current_watchlist_name: str = ""
        self._current_watchlist_desc: str = ""
        self._current_watchlist_count: int = 0

        self._summary_gainers: int = 0
        self._summary_losers: int = 0
        self._summary_avg_change: str = "%0.00"
        self._is_refreshing: bool = False

        self._load_watchlists()

    # --- Properties ---

    @Property(list, notify=watchlistsChanged)
    def watchlists(self) -> List[Dict[str, Any]]:
        return self._watchlists

    @Property(int, notify=currentWatchlistChanged)
    def currentWatchlistId(self) -> int:
        return self._current_watchlist_id

    @Property(str, notify=currentWatchlistChanged)
    def currentWatchlistName(self) -> str:
        return self._current_watchlist_name

    @Property(str, notify=currentWatchlistChanged)
    def currentWatchlistDesc(self) -> str:
        return self._current_watchlist_desc

    @Property(int, notify=currentWatchlistChanged)
    def currentWatchlistCount(self) -> int:
        return self._current_watchlist_count

    @Property(QObject, constant=True)
    def stocksModel(self) -> WatchlistTableModel:
        return self._stocks_model

    @Property(int, notify=stocksChanged)
    def summaryGainersCount(self) -> int:
        return self._summary_gainers

    @Property(int, notify=stocksChanged)
    def summaryLosersCount(self) -> int:
        return self._summary_losers

    @Property(str, notify=stocksChanged)
    def summaryAvgChange(self) -> str:
        return self._summary_avg_change

    @Property(bool, notify=refreshStateChanged)
    def isRefreshing(self) -> bool:
        return self._is_refreshing

    # --- Data Loading & Processing ---

    def _get_watchlist_service(self):
        if self._container and hasattr(self._container, "services") and hasattr(self._container.services, "watchlist_service"):
            return self._container.services.watchlist_service
        return None

    @Slot(int, int)
    def moveWatchlist(self, from_index: int, to_index: int) -> None:
        """Listeyi sürükle-bırak ile yeni sıraya taşır ve sırayı kalıcı kaydeder."""
        ws = self._get_watchlist_service()
        size = len(self._watchlists)
        if not (0 <= from_index < size and 0 <= to_index < size) or from_index == to_index:
            return
        reordered = list(self._watchlists)
        reordered.insert(to_index, reordered.pop(from_index))
        if ws is not None:
            try:
                ws.reorder_watchlists([w["id"] for w in reordered])
            except Exception as exc:
                logger.error("Watchlist sırası kaydedilemedi: %s", exc)
                self.actionCompleted.emit(False, f"Sıra kaydedilemedi: {exc}")
                return
        self._watchlists = reordered
        self.watchlistsChanged.emit()

    @Slot()
    def reloadAll(self) -> None:
        """Dışarıdan veri değişince (sistem sıfırlama vb.) listeleri DB'den yeniden okur."""
        self._load_watchlists()

    def _load_watchlists(self) -> None:
        ws = self._get_watchlist_service()
        if not ws:
            # Fallback/Mock veri
            self._watchlists = [
                {"id": 1, "name": "BIST 30 Favoriler", "description": "Öncü sanayi ve bankacılık hisseleri", "count": 3, "avgDiff": "+1.85%", "isUp": True},
                {"id": 2, "name": "Büyüme & Teknoloji", "description": "Yüksek büyüme potansiyelli teknoloji şirketleri", "count": 2, "avgDiff": "-0.40%", "isUp": False},
            ]
            if self._watchlists:
                self.selectWatchlist(self._watchlists[0]["id"])
            self.watchlistsChanged.emit()
            return

        try:
            raw_lists = ws.get_all_watchlists()
            result = []
            for w in raw_lists:
                count = ws.get_watchlist_item_count(w.id)
                result.append({
                    "id": w.id,
                    "name": w.name,
                    "description": w.description or "",
                    "count": count,
                })
            self._watchlists = result
            self.watchlistsChanged.emit()

            # Varsayılan seçim
            if self._watchlists:
                # Eğer daha önce seçili id listede varsa onu koru, yoksa ilkini seç
                target_id = self._current_watchlist_id if any(wl["id"] == self._current_watchlist_id for wl in self._watchlists) else self._watchlists[0]["id"]
                self.selectWatchlist(target_id)
            else:
                self._current_watchlist_id = -1
                self._current_watchlist_name = ""
                self._current_watchlist_desc = ""
                self._current_watchlist_count = 0
                self._stocks_model.clear()
                self.currentWatchlistChanged.emit()
                self.stocksChanged.emit()

        except Exception as exc:
            logger.error("Watchlist listesi yuklenirken hata: %s", exc)

    def _load_stocks(self, watchlist_id: int) -> None:
        ws = self._get_watchlist_service()
        if not ws:
            # Fallback mock stocks
            mock_stocks = [
                {
                    "ticker": "THYAO.IS",
                    "cleanTicker": "THYAO",
                    "companyName": "Türk Hava Yolları",
                    "priceRaw": 294.25,
                    "dailyDiffRaw": 2.15,
                    "dayLow": 289.50,
                    "dayHigh": 296.00,
                    "dayRangePct": 0.73,
                    "volume": "1.42 Mr ₺",
                    "sparkline": [282.0, 284.5, 283.0, 288.0, 289.5, 292.0, 294.25],
                    "notes": "2026 Q3 güçlü kargo gelirleri bekleniyor",
                    "stockId": 1,
                    "itemId": 1,
                    "flashState": 0,
                },
                {
                    "ticker": "ASELS.IS",
                    "cleanTicker": "ASELS",
                    "companyName": "Aselsan Elektronik",
                    "priceRaw": 62.40,
                    "dailyDiffRaw": -0.80,
                    "dayLow": 61.80,
                    "dayHigh": 63.20,
                    "dayRangePct": 0.43,
                    "volume": "840 Mn ₺",
                    "sparkline": [64.0, 63.5, 64.2, 63.0, 62.8, 62.9, 62.4],
                    "notes": "Yeni radar ve haberleşme teslimatları",
                    "stockId": 2,
                    "itemId": 2,
                    "flashState": 0,
                },
            ]
            self._stocks_model.set_stocks(mock_stocks)
            self._update_summaries(mock_stocks)
            return

        try:
            raw_stocks = ws.get_watchlist_stocks(watchlist_id)
            stock_data_list: List[Dict[str, Any]] = []

            price_repo = None
            if self._container and hasattr(self._container, "repositories"):
                price_repo = getattr(self._container.repositories, "price_repo", None)

            start_date = date.today() - timedelta(days=90)
            end_date = date.today()

            # N+1 Önleme: Tüm hisselerin fiyat serilerini tek toplu sorguyla çek
            bulk_price_map: Dict[int, Any] = {}
            if price_repo:
                valid_sids = [
                    (it.get("stock").id if it.get("stock") else (it.get("item").stock_id if it.get("item") else 0))
                    for it in raw_stocks
                ]
                valid_sids = [sid for sid in valid_sids if sid > 0]
                if valid_sids:
                    try:
                        bulk_price_map = price_repo.get_price_series_bulk(valid_sids, start_date, end_date)
                    except Exception as exc:
                        logger.warning("Toplu fiyat serisi alinamadi: %s", exc)

            for item_dict in raw_stocks:
                item = item_dict.get("item")
                stock = item_dict.get("stock")
                ticker = item_dict.get("ticker", "")
                name = item_dict.get("name", ticker)
                notes = item.notes if item else ""
                stock_id = stock.id if stock else (item.stock_id if item else 0)
                item_id = item.id if item else 0

                # Fiyat ve geçmiş seri çözümlemesi (O(1) toplu map erişimi)
                hist_bars = bulk_price_map.get(stock_id, [])

                if hist_bars:
                    last_bar = hist_bars[-1]
                    price_val = float(last_bar.close_price)
                    prev_close = float(hist_bars[-2].close_price) if len(hist_bars) > 1 else price_val
                    daily_diff = ((price_val - prev_close) / prev_close * 100) if prev_close > 0 else 0.0

                    low_val = float(last_bar.low_price) if getattr(last_bar, "low_price", None) else price_val * 0.985
                    high_val = float(last_bar.high_price) if getattr(last_bar, "high_price", None) else price_val * 1.015
                    day_range_span = max(0.01, high_val - low_val)
                    day_range_pct = max(0.0, min(1.0, (price_val - low_val) / day_range_span))

                    vol_raw = getattr(last_bar, "volume", None)
                    vol_text = f"{float(vol_raw)/1e6:.1f}M" if vol_raw else "-"

                    sparkline_pts = [float(b.close_price) for b in hist_bars[-10:]]
                else:
                    # Fiyat yoksa varsayılan
                    price_val = 100.0
                    daily_diff = 0.0
                    low_val = 98.0
                    high_val = 102.0
                    day_range_pct = 0.5
                    vol_text = "-"
                    sparkline_pts = [100.0, 100.0]

                stock_data_list.append({
                    "ticker": ticker,
                    "cleanTicker": ticker.replace(".IS", ""),
                    "companyName": name if name and name != ticker else ticker.replace(".IS", ""),
                    "priceRaw": price_val,
                    "dailyDiffRaw": daily_diff,
                    "dayLow": low_val,
                    "dayHigh": high_val,
                    "dayRangePct": day_range_pct,
                    "volume": vol_text,
                    "sparkline": sparkline_pts,
                    "notes": notes or "",
                    "stockId": stock_id,
                    "itemId": item_id,
                    "flashState": 0,
                })

            self._stocks_model.set_stocks(stock_data_list)
            self._update_summaries(stock_data_list)

        except Exception as exc:
            logger.error("Hisseler yuklenirken hata (%s): %s", watchlist_id, exc)

    def _update_summaries(self, stocks_list: List[Dict[str, Any]]) -> None:
        gainers = sum(1 for s in stocks_list if s.get("dailyDiffRaw", 0.0) > 0)
        losers = sum(1 for s in stocks_list if s.get("dailyDiffRaw", 0.0) < 0)
        total = len(stocks_list)

        if total > 0:
            avg_diff = sum(s.get("dailyDiffRaw", 0.0) for s in stocks_list) / total
            sign = "+" if avg_diff >= 0 else ""
            self._summary_avg_change = f"{sign}%{avg_diff:.2f}"
        else:
            self._summary_avg_change = "%0.00"

        self._summary_gainers = gainers
        self._summary_losers = losers
        self.stocksChanged.emit()

    # --- Public Slots for QML ---

    @Slot(int)
    def selectWatchlist(self, watchlist_id: int) -> None:
        self._current_watchlist_id = watchlist_id
        for w in self._watchlists:
            if w["id"] == watchlist_id:
                self._current_watchlist_name = w["name"]
                self._current_watchlist_desc = w["description"]
                self._current_watchlist_count = w["count"]
                break

        self.currentWatchlistChanged.emit()
        self._load_stocks(watchlist_id)

    @Slot(str, str)
    def createWatchlist(self, name: str, description: str = "") -> None:
        name = name.strip()
        if not name:
            self.actionCompleted.emit(False, "Liste adı boş olamaz!")
            return

        ws = self._get_watchlist_service()
        if not ws:
            new_id = len(self._watchlists) + 10
            self._watchlists.append({"id": new_id, "name": name, "description": description, "count": 0})
            self.watchlistsChanged.emit()
            self.selectWatchlist(new_id)
            self.actionCompleted.emit(True, f"'{name}' listesi oluşturuldu.")
            return

        try:
            created = ws.create_watchlist(name, description)
            self._load_watchlists()
            self.selectWatchlist(created.id)
            self.actionCompleted.emit(True, f"'{name}' listesi başarıyla oluşturuldu.")
        except Exception as exc:
            logger.error("Watchlist olusturulamadi: %s", exc)
            self.actionCompleted.emit(False, str(exc))

    @Slot(int, str, str)
    def updateWatchlist(self, watchlist_id: int, name: str, description: str = "") -> None:
        name = name.strip()
        if not name:
            self.actionCompleted.emit(False, "Liste adı boş olamaz!")
            return

        ws = self._get_watchlist_service()
        if not ws:
            for w in self._watchlists:
                if w["id"] == watchlist_id:
                    w["name"] = name
                    w["description"] = description
                    break
            self.watchlistsChanged.emit()
            self.selectWatchlist(watchlist_id)
            self.actionCompleted.emit(True, f"'{name}' güncellendi.")
            return

        try:
            ws.update_watchlist(watchlist_id, name, description)
            self._load_watchlists()
            self.selectWatchlist(watchlist_id)
            self.actionCompleted.emit(True, f"'{name}' listesi güncellendi.")
        except Exception as exc:
            logger.error("Watchlist guncellenemedi: %s", exc)
            self.actionCompleted.emit(False, str(exc))

    @Slot(int)
    def deleteWatchlist(self, watchlist_id: int) -> None:
        ws = self._get_watchlist_service()
        if not ws:
            self._watchlists = [w for w in self._watchlists if w["id"] != watchlist_id]
            self.watchlistsChanged.emit()
            if self._watchlists:
                self.selectWatchlist(self._watchlists[0]["id"])
            self.actionCompleted.emit(True, "Liste silindi.")
            return

        try:
            ws.delete_watchlist(watchlist_id)
            self._load_watchlists()
            self.actionCompleted.emit(True, "Liste başarıyla silindi.")
        except Exception as exc:
            logger.error("Watchlist silinemedi: %s", exc)
            self.actionCompleted.emit(False, str(exc))

    @Slot(int, str, str)
    def addStock(self, watchlist_id: int, ticker: str, notes: str = "") -> None:
        ticker = clean_ticker(ticker)
        if not ticker:
            self.actionCompleted.emit(False, "Hisse kodu boş olamaz!")
            return

        ws = self._get_watchlist_service()
        if not ws:
            current_stocks = self._stocks_model._stocks
            current_stocks.append({
                "ticker": ticker,
                "cleanTicker": ticker.replace(".IS", ""),
                "companyName": ticker.replace(".IS", ""),
                "priceRaw": 150.0,
                "dailyDiffRaw": 1.25,
                "dayLow": 147.0,
                "dayHigh": 152.0,
                "dayRangePct": 0.60,
                "volume": "500 Mn ₺",
                "sparkline": [146.0, 148.0, 149.0, 150.0],
                "notes": notes,
                "stockId": len(current_stocks) + 1,
                "itemId": len(current_stocks) + 1,
                "flashState": 1,
            })
            self._stocks_model.set_stocks(current_stocks)
            self._update_summaries(current_stocks)
            self.actionCompleted.emit(True, f"{ticker} listeye eklendi.")
            return

        try:
            ws.add_stock_by_ticker(watchlist_id, ticker, notes)
            self._load_stocks(watchlist_id)
            # Listenin sayaç bilgisini yenile
            self._load_watchlists()
            self.selectWatchlist(watchlist_id)
            self.actionCompleted.emit(True, f"{ticker} listeye başarıyla eklendi.")
        except Exception as exc:
            logger.error("Hisse eklenemedi: %s", exc)
            self.actionCompleted.emit(False, str(exc))

    @Slot(int, int)
    def removeStock(self, watchlist_id: int, stock_id: int) -> None:
        ws = self._get_watchlist_service()
        if not ws:
            current_stocks = [s for s in self._stocks_model._stocks if s["stockId"] != stock_id]
            self._stocks_model.set_stocks(current_stocks)
            self._update_summaries(current_stocks)
            self.actionCompleted.emit(True, "Hisse listeden çıkarıldı.")
            return

        try:
            ws.remove_stock_from_watchlist(watchlist_id, stock_id)
            self._load_stocks(watchlist_id)
            self._load_watchlists()
            self.selectWatchlist(watchlist_id)
            self.actionCompleted.emit(True, "Hisse listeden başarıyla çıkarıldı.")
        except Exception as exc:
            logger.error("Hisse cikarilamadi: %s", exc)
            self.actionCompleted.emit(False, str(exc))

    @Slot(int, int, str)
    def updateStockNotes(self, watchlist_id: int, stock_id: int, notes: str) -> None:
        ws = self._get_watchlist_service()
        if not ws:
            for s in self._stocks_model._stocks:
                if s["stockId"] == stock_id:
                    s["notes"] = notes
                    break
            self._stocks_model.set_stocks(self._stocks_model._stocks)
            self.actionCompleted.emit(True, "Not güncellendi.")
            return

        try:
            ws.update_watchlist_item_notes(watchlist_id, stock_id, notes)
            self._load_stocks(watchlist_id)
            self.actionCompleted.emit(True, "Hisse notu başarıyla güncellendi.")
        except Exception as exc:
            logger.error("Hisse notu guncellenemedi: %s", exc)
            self.actionCompleted.emit(False, str(exc))

    @Slot()
    def refreshPrices(self) -> None:
        self._is_refreshing = True
        self.refreshStateChanged.emit(True)

        if self._current_watchlist_id > 0:
            self._load_stocks(self._current_watchlist_id)

        QTimer.singleShot(600, lambda: self._finish_refresh())

    def _finish_refresh(self) -> None:
        self._is_refreshing = False
        self.refreshStateChanged.emit(False)
        self.actionCompleted.emit(True, "İzleme listesi fiyatları güncellendi.")

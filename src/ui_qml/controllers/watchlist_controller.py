"""
WatchlistController — WatchlistView'un veri köprüsü (bkz. plan §7.3/§9.5, d3).

Birden fazla liste, hızlı ekle/çıkar, fiyat/günlük % kolonu. Liste CRUD'u
`WatchlistService`'e delege edilir (mevcut, hiç değiştirilmedi). Fiyat/günlük %
`Stock360Service.get_overview()`'e delege edilir (§5.1) — sadece lokal DB'deki
son kapanış, canlı API çağrısı yapılmaz (ScreenerService ile aynı ilke, §9.6).
"""
from __future__ import annotations

from typing import Any, List

from src.qt_compat.qtcore import Property, QObject, Signal, Slot


def _to_float(value: Any) -> float:
    return float(value) if value is not None else 0.0


class WatchlistController(QObject):
    """Watchlist listeleri + aktif listenin hisseleri (ticker/isim/fiyat/günlük %)."""

    watchlistsChanged = Signal()
    activeWatchlistIdChanged = Signal()
    itemsChanged = Signal()
    errorChanged = Signal()

    def __init__(self, container, parent=None) -> None:
        super().__init__(parent)
        self._container = container
        self._watchlist_ids: List[int] = []
        self._watchlist_names: List[str] = []
        self._active_watchlist_id: int = -1

        self._item_tickers: List[str] = []
        self._item_names: List[str] = []
        self._item_prices: List[float] = []
        self._item_daily_change_pct: List[float] = []

        self._error = ""
        self.refreshWatchlists()

    # ------------------------------------------------------------------
    # Liste seçici
    # ------------------------------------------------------------------

    @Property("QVariantList", notify=watchlistsChanged)
    def watchlistIds(self) -> List[int]:
        return list(self._watchlist_ids)

    @Property("QVariantList", notify=watchlistsChanged)
    def watchlistNames(self) -> List[str]:
        return list(self._watchlist_names)

    @Property(int, notify=activeWatchlistIdChanged)
    def activeWatchlistId(self) -> int:
        return self._active_watchlist_id

    @Property(str, notify=errorChanged)
    def error(self) -> str:
        return self._error

    @Slot()
    def refreshWatchlists(self) -> None:
        watchlists = self._container.watchlist_service.get_all_watchlists()
        self._watchlist_ids = [w.id for w in watchlists]
        self._watchlist_names = [w.name for w in watchlists]
        self.watchlistsChanged.emit()

        if self._active_watchlist_id not in self._watchlist_ids:
            new_active = self._watchlist_ids[0] if self._watchlist_ids else -1
            self._set_active_watchlist_id(new_active)
        self._refresh_items()

    @Slot(int)
    def selectWatchlist(self, watchlist_id: int) -> None:
        if watchlist_id not in self._watchlist_ids or watchlist_id == self._active_watchlist_id:
            return
        self._set_active_watchlist_id(watchlist_id)
        self._refresh_items()

    @Slot(str)
    def createWatchlist(self, name: str) -> None:
        try:
            watchlist = self._container.watchlist_service.create_watchlist(name)
        except ValueError as exc:
            self._set_error(str(exc))
            return
        self._set_error("")
        self.refreshWatchlists()
        self.selectWatchlist(watchlist.id)

    @Slot()
    def deleteActiveWatchlist(self) -> None:
        if self._active_watchlist_id < 0:
            return
        self._container.watchlist_service.delete_watchlist(self._active_watchlist_id)
        self._active_watchlist_id = -1
        self.refreshWatchlists()

    # ------------------------------------------------------------------
    # Aktif listenin hisseleri
    # ------------------------------------------------------------------

    @Property("QVariantList", notify=itemsChanged)
    def itemTickers(self) -> List[str]:
        return list(self._item_tickers)

    @Property("QVariantList", notify=itemsChanged)
    def itemNames(self) -> List[str]:
        return list(self._item_names)

    @Property("QVariantList", notify=itemsChanged)
    def itemPrices(self) -> List[float]:
        return list(self._item_prices)

    @Property("QVariantList", notify=itemsChanged)
    def itemDailyChangePct(self) -> List[float]:
        return list(self._item_daily_change_pct)

    @Slot(str)
    def addTicker(self, ticker: str) -> None:
        if self._active_watchlist_id < 0:
            self._set_error("Önce bir liste seçin veya oluşturun.")
            return
        try:
            self._container.watchlist_service.add_stock_by_ticker(self._active_watchlist_id, ticker)
        except ValueError as exc:
            self._set_error(str(exc))
            return
        self._set_error("")
        self._refresh_items()

    @Slot(str)
    def removeTicker(self, ticker: str) -> None:
        if self._active_watchlist_id < 0:
            return
        stock = self._container.stock_repo.get_stock_by_ticker(ticker.strip().upper())
        if stock is None or stock.id is None:
            return
        self._container.watchlist_service.remove_stock_from_watchlist(self._active_watchlist_id, stock.id)
        self._refresh_items()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _refresh_items(self) -> None:
        if self._active_watchlist_id < 0:
            self._item_tickers, self._item_names = [], []
            self._item_prices, self._item_daily_change_pct = [], []
            self.itemsChanged.emit()
            return

        stocks_info = self._container.watchlist_service.get_watchlist_stocks(self._active_watchlist_id)
        tickers = [info["ticker"] for info in stocks_info]
        names = [info["name"] for info in stocks_info]
        prices: List[float] = []
        changes: List[float] = []
        for ticker in tickers:
            overview = self._container.stock_360_service.get_overview(ticker)
            prices.append(_to_float(overview.last_price) if overview else 0.0)
            changes.append(_to_float(overview.daily_change_pct) if overview else 0.0)

        self._item_tickers = tickers
        self._item_names = names
        self._item_prices = prices
        self._item_daily_change_pct = changes
        self.itemsChanged.emit()

    def _set_active_watchlist_id(self, watchlist_id: int) -> None:
        if watchlist_id != self._active_watchlist_id:
            self._active_watchlist_id = watchlist_id
            self.activeWatchlistIdChanged.emit()

    def _set_error(self, message: str) -> None:
        if message != self._error:
            self._error = message
            self.errorChanged.emit()

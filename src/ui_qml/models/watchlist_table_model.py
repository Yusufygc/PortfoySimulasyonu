"""
Watchlist Table Model — QML için optimize edilmiş takip listesi hisseleri list/table modeli.
"""
from __future__ import annotations

from typing import List, Dict, Any
from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    Qt,
    QByteArray,
    Signal,
)


class WatchlistTableModel(QAbstractListModel):
    # Roller
    TickerRole = Qt.UserRole + 1
    CleanTickerRole = Qt.UserRole + 2
    CompanyNameRole = Qt.UserRole + 3
    PriceRole = Qt.UserRole + 4
    PriceRawRole = Qt.UserRole + 5
    DailyDiffRole = Qt.UserRole + 6
    DailyDiffRawRole = Qt.UserRole + 7
    IsUpRole = Qt.UserRole + 8
    DayLowRole = Qt.UserRole + 9
    DayHighRole = Qt.UserRole + 10
    DayRangePctRole = Qt.UserRole + 11
    VolumeRole = Qt.UserRole + 12
    SparklineRole = Qt.UserRole + 13
    NotesRole = Qt.UserRole + 14
    StockIdRole = Qt.UserRole + 15
    ItemIdRole = Qt.UserRole + 16
    FlashStateRole = Qt.UserRole + 17

    countChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stocks: List[Dict[str, Any]] = []

    def roleNames(self) -> Dict[int, QByteArray]:
        return {
            self.TickerRole: QByteArray(b"ticker"),
            self.CleanTickerRole: QByteArray(b"cleanTicker"),
            self.CompanyNameRole: QByteArray(b"companyName"),
            self.PriceRole: QByteArray(b"price"),
            self.PriceRawRole: QByteArray(b"priceRaw"),
            self.DailyDiffRole: QByteArray(b"dailyDiff"),
            self.DailyDiffRawRole: QByteArray(b"dailyDiffRaw"),
            self.IsUpRole: QByteArray(b"isUp"),
            self.DayLowRole: QByteArray(b"dayLow"),
            self.DayHighRole: QByteArray(b"dayHigh"),
            self.DayRangePctRole: QByteArray(b"dayRangePct"),
            self.VolumeRole: QByteArray(b"volume"),
            self.SparklineRole: QByteArray(b"sparkline"),
            self.NotesRole: QByteArray(b"notes"),
            self.StockIdRole: QByteArray(b"stockId"),
            self.ItemIdRole: QByteArray(b"itemId"),
            self.FlashStateRole: QByteArray(b"flashState"),
        }

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._stocks)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._stocks):
            return None

        s = self._stocks[index.row()]

        if role == self.TickerRole:
            return s.get("ticker", "")
        elif role == self.CleanTickerRole:
            t = s.get("ticker", "")
            return t.replace(".IS", "")
        elif role == self.CompanyNameRole:
            return s.get("companyName", "")
        elif role == self.PriceRole:
            price = s.get("priceRaw", 0.0)
            return f"₺{price:,.2f}"
        elif role == self.PriceRawRole:
            return float(s.get("priceRaw", 0.0))
        elif role == self.DailyDiffRole:
            diff = s.get("dailyDiffRaw", 0.0)
            if diff > 0:
                return f"+%{diff:.2f}"
            elif diff < 0:
                return f"-%{abs(diff):.2f}"
            else:
                return "%0.00"
        elif role == self.DailyDiffRawRole:
            return float(s.get("dailyDiffRaw", 0.0))
        elif role == self.IsUpRole:
            return s.get("dailyDiffRaw", 0.0) >= 0
        elif role == self.DayLowRole:
            low = s.get("dayLow", 0.0)
            return f"₺{low:,.2f}"
        elif role == self.DayHighRole:
            high = s.get("dayHigh", 0.0)
            return f"₺{high:,.2f}"
        elif role == self.DayRangePctRole:
            return float(s.get("dayRangePct", 0.5))
        elif role == self.VolumeRole:
            return s.get("volume", "-")
        elif role == self.SparklineRole:
            return s.get("sparkline", [])
        elif role == self.NotesRole:
            return s.get("notes", "") or ""
        elif role == self.StockIdRole:
            return int(s.get("stockId", 0))
        elif role == self.ItemIdRole:
            return int(s.get("itemId", 0))
        elif role == self.FlashStateRole:
            return int(s.get("flashState", 0))

        return None

    def set_stocks(self, stocks_data: List[Dict[str, Any]]) -> None:
        self.beginResetModel()
        self._stocks = list(stocks_data)
        self.endResetModel()
        self.countChanged.emit(len(self._stocks))

    def clear(self) -> None:
        self.beginResetModel()
        self._stocks.clear()
        self.endResetModel()
        self.countChanged.emit(0)

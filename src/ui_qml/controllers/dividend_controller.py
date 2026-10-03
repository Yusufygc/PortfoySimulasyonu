"""
DividendController — ana portföydeki bir hissenin nakit temettü kayıtları (QML).

Temettü, hissenin portföyde bulunduğu bir tarihte alınan net nakit tutardır: nakit bakiyeye girer ve portföy getirisi
(TWR) olarak sayılır; dış sermaye girişi değildir. Kayıt ve silme application servisleri üzerinden yapılır.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.ui_qml.controllers.number_input import parse_decimal_text

logger = logging.getLogger(__name__)


def _clean_ticker(ticker: str) -> str:
    return (ticker or "").replace(".IS", "").strip().upper()


def _fmt_tr(value: Decimal) -> str:
    """1234.5 -> '1.234,50' (Türkçe sayı biçimi)."""
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_amount(text: str) -> Optional[Decimal]:
    """'1.234,56', '1234.56' veya '50.000' -> Decimal; geçersiz veya pozitif olmayan değer için None."""
    value = parse_decimal_text(text)
    return value if value is not None and value > 0 else None


def parse_date(text: str) -> Optional[date]:
    text = (text or "").strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


class DividendController(QObject):
    """QML context property: dividendController"""

    dividendsChanged = Signal()
    # (success, message) — diyalog durum satırı için
    notification = Signal(bool, str, arguments=["success", "message"])
    # Nakit bakiyesi değişti; Dashboard yenilenmeli
    portfolioChanged = Signal()

    def __init__(self, container=None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._ticker = ""
        self._stock_id: Optional[int] = None
        self._dividends: List[Dict[str, Any]] = []
        self._total = Decimal("0")

    def _svc(self, name: str):
        return getattr(self._container, name, None) if self._container else None

    # ------------------------------------------------------------------ properties

    @Property(str, notify=dividendsChanged)
    def ticker(self) -> str:
        return self._ticker

    @Property("QVariantList", notify=dividendsChanged)
    def dividends(self) -> List[Dict[str, Any]]:
        return self._dividends

    @Property(str, notify=dividendsChanged)
    def totalText(self) -> str:
        return f"{_fmt_tr(self._total)} ₺"

    @Property(bool, notify=dividendsChanged)
    def hasDividends(self) -> bool:
        return bool(self._dividends)

    # ------------------------------------------------------------------ slots

    @Slot(str)
    def loadFor(self, ticker: str) -> None:
        """Hissenin temettü kayıtlarını yükler."""
        self._ticker = _clean_ticker(ticker)
        self._stock_id = None
        lookup = self._svc("stock_lookup_service")
        if lookup is not None:
            stock = lookup.find_stock(self._ticker)
            self._stock_id = stock.id if stock is not None else None
        self._reload()

    @Slot(str, str, str)
    def addDividend(self, amount_text: str, date_text: str, note: str) -> None:
        service = self._svc("cash_movement_service")
        if service is None or self._stock_id is None:
            self.notification.emit(False, "Temettü servisi kullanılamıyor.")
            return
        amount = parse_amount(amount_text)
        if amount is None:
            self.notification.emit(False, "Tutar 0'dan büyük geçerli bir sayı olmalıdır.")
            return
        movement_date = parse_date(date_text)
        if movement_date is None:
            self.notification.emit(False, "Tarih geçersiz. Biçim: YYYY-AA-GG")
            return
        try:
            service.add_dividend(
                self._stock_id, amount, movement_date,
                notes=(note or "").strip() or f"{self._ticker} temettü",
            )
        except ValueError as exc:
            self.notification.emit(False, str(exc))
            return
        except Exception as exc:
            logger.warning("Temettü kaydedilemedi (%s): %s", self._ticker, exc)
            self.notification.emit(False, "Temettü kaydedilemedi.")
            return
        self._reload()
        self.portfolioChanged.emit()
        self.notification.emit(True, f"{_fmt_tr(amount)} ₺ temettü nakit bakiyeye eklendi.")

    @Slot(int)
    def deleteDividend(self, movement_id: int) -> None:
        service = self._svc("cash_movement_service")
        if service is None:
            self.notification.emit(False, "Temettü servisi kullanılamıyor.")
            return
        try:
            service.delete_dividend(movement_id)
        except ValueError as exc:
            self.notification.emit(False, str(exc))
            return
        except Exception as exc:
            logger.warning("Temettü silinemedi (%s): %s", movement_id, exc)
            self.notification.emit(False, "Temettü silinemedi.")
            return
        self._reload()
        self.portfolioChanged.emit()
        self.notification.emit(True, "Temettü kaydı silindi.")

    # ------------------------------------------------------------------ internal

    def _reload(self) -> None:
        service = self._svc("cash_movement_service")
        rows: List[Dict[str, Any]] = []
        total = Decimal("0")
        if service is not None and self._stock_id is not None:
            try:
                movements = service.get_dividends(self._stock_id)
            except Exception as exc:
                logger.warning("Temettü kayıtları okunamadı (%s): %s", self._ticker, exc)
                movements = []
            for movement in reversed(movements):  # en yeni üstte
                total += movement.amount
                rows.append({
                    "id": int(movement.id or 0),
                    "dateText": movement.movement_date.strftime("%d.%m.%Y"),
                    "amountText": f"{_fmt_tr(movement.amount)} ₺",
                    "note": movement.notes or "",
                })
        self._dividends = rows
        self._total = total
        self.dividendsChanged.emit()

"""
CashPoolController — Portföyüm > ortak nakit havuzu (TL + USD) ve Döviz Al/Sat (QML).

Yalnızca `CashPoolService` ve `FxConversionService` üzerinden çalışır; bakiyeler olaylardan türetilir. Döviz işlemleri
hızlıdır (yerel veritabanı), bu yüzden arka plan iş parçacığı kullanılmaz. Bakiye değişince `balancesChanged` yayınlanır
(Portföyüm ve Ana Sayfa yeniden okur).
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.domain.market_clock import market_time, market_today
from src.domain.models.fx_conversion import FxSide
from src.ui_qml.controllers.number_input import parse_decimal_text
from src.ui_qml.messages import msg
from src.ui_qml.presenters.formatting import input_decimal, tr_number

logger = logging.getLogger(__name__)


def _parse_date(text: str) -> Optional[date]:
    try:
        return datetime.strptime((text or "").strip(), "%d.%m.%Y").date()
    except ValueError:
        return None


def _parse_time(text: str) -> Optional[time]:
    try:
        return datetime.strptime((text or "").strip(), "%H:%M").time()
    except ValueError:
        return None


def _parse_moment(day: str, at: str) -> Tuple[Optional[Tuple[date, time]], str]:
    """(gün, saat) ve hata metni: boş alan bugün/şimdi sayılır; yazılmış ama geçersiz ya da gelecek değer hatadır."""
    day_text, time_text = (day or "").strip(), (at or "").strip()
    conversion_date = _parse_date(day_text) if day_text else market_today()
    if conversion_date is None:
        return None, msg("cash_pool.invalid_date")
    if conversion_date > market_today():
        return None, msg("cash_pool.future_date")
    conversion_time = _parse_time(time_text) if time_text else market_time()
    if conversion_time is None:
        return None, msg("cash_pool.invalid_time")
    return (conversion_date, conversion_time), ""


def _positive(text: str) -> Optional[Decimal]:
    value = parse_decimal_text(text)
    return value if value is not None and value > 0 else None


def _non_negative(text: str) -> Optional[Decimal]:
    if not (text or "").strip():
        return Decimal("0")
    value = parse_decimal_text(text)
    return value if value is not None and value >= 0 else None


class CashPoolController(QObject):
    balancesChanged = Signal()
    notify = Signal(bool, str, arguments=["success", "message"])

    def __init__(self, container=None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._pool = getattr(container, "cash_pool_service", None) if container else None
        self._fx = getattr(container, "fx_conversion_service", None) if container else None
        self._rates = getattr(container, "fx_rate_service", None) if container else None
        self._balances = {"TRY": Decimal("0"), "USD": Decimal("0")}
        self._conversions: List[Dict[str, Any]] = []
        self.reload()

    @Property(str, notify=balancesChanged)
    def tryBalance(self) -> str:
        return f"₺{tr_number(self._balances['TRY'])}"

    @Property(str, notify=balancesChanged)
    def usdBalance(self) -> str:
        return f"${tr_number(self._balances['USD'])}"

    @Property(float, notify=balancesChanged)
    def usdBalanceValue(self) -> float:
        return float(self._balances["USD"])

    @Property(float, notify=balancesChanged)
    def tryBalanceValue(self) -> float:
        return float(self._balances["TRY"])

    @Property("QVariantList", notify=balancesChanged)
    def conversions(self) -> List[Dict[str, Any]]:
        return self._conversions

    @Slot()
    def reload(self) -> None:
        """Bakiyeleri ve döviz geçmişini veritabanından yeniden okur; değişiklik varsa `balancesChanged` yayınlar."""
        if self._pool is None:
            return
        try:
            balances = self._pool.balances()
            conversions = self._conversion_rows()
        except Exception as exc:  # veri okunamazsa eski görünüm kalır
            logger.warning("Nakit havuzu bakiyeleri okunamadı: %s", exc, exc_info=True)
            return
        if balances != self._balances or conversions != self._conversions:
            self._balances, self._conversions = balances, conversions
            self.balancesChanged.emit()

    def _conversion_rows(self) -> List[Dict[str, Any]]:
        if self._fx is None:
            return []
        rows = []
        for item in reversed(self._fx.list_conversions()):
            buy = item.side == FxSide.BUY_USD
            rows.append({
                "id": item.id,
                "text": msg("cash_pool.row", side=msg("cash_pool.buy") if buy else msg("cash_pool.sell"),
                            usd=tr_number(item.usd_amount), rate=tr_number(item.rate, 4),
                            day=item.conversion_date.strftime("%d.%m.%Y")),
            })
        return rows

    @Slot(result=str)
    def suggestRate(self) -> str:
        """Önerilen USD/TRY kuru (veritabanındaki en yeni kur); yoksa boş."""
        rate = self._rates.get_rate("USD", "TRY") if self._rates is not None else None
        return input_decimal(rate) if rate is not None else ""

    @Slot(str, str, str, str, str)
    def buyUsd(self, amount: str, rate: str, day: str, at: str, fee: str) -> None:
        self._convert(True, (amount, rate, day, at, fee))

    @Slot(str, str, str, str, str)
    def sellUsd(self, amount: str, rate: str, day: str, at: str, fee: str) -> None:
        self._convert(False, (amount, rate, day, at, fee))

    @staticmethod
    def _parse_form(form: Tuple[str, ...]) -> Tuple[Optional[dict], str]:
        """(seçenekler, hata metni): form metinlerini sayı ve tarihe çevirir; hata varsa seçenekler None."""
        amount, rate, day, at, fee = form
        usd, rate_value, fee_value = _positive(amount), _positive(rate), _non_negative(fee)
        checks = ((usd, msg("cash_pool.invalid_amount")), (rate_value, msg("cash_pool.invalid_rate")), (fee_value, msg("cash_pool.invalid_fee")))
        for value, error in checks:
            if value is None:
                return None, error
        moment, error = _parse_moment(day, at)
        if moment is None:
            return None, error
        return {"usd": usd, "rate": rate_value, "conversion_date": moment[0], "conversion_time": moment[1],
                "fee_try": fee_value}, ""

    def _convert(self, buy: bool, form: Tuple[str, ...]) -> None:
        if self._fx is None:
            self.notify.emit(False, msg("cash_pool.service_missing"))
            return
        values, error = self._parse_form(form)
        if values is None:
            self.notify.emit(False, error)
            return
        usd, rate = values.pop("usd"), values.pop("rate")
        try:
            (self._fx.buy_usd if buy else self._fx.sell_usd)(usd, rate=rate, **values)
        except ValueError as exc:
            self.notify.emit(False, str(exc))
            return
        self.reload()
        done = msg("cash_pool.done_buy", usd=tr_number(usd)) if buy else msg("cash_pool.done_sell", usd=tr_number(usd))
        self.notify.emit(True, done)

    @Slot(int)
    def deleteConversion(self, conversion_id: int) -> None:
        if self._fx is None:
            return
        try:
            self._fx.delete_conversion(conversion_id)
        except ValueError as exc:
            self.notify.emit(False, str(exc))
            return
        self.reload()
        self.notify.emit(True, msg("cash_pool.deleted"))

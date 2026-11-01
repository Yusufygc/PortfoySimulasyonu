"""
MyPortfolioController — Portföyüm sayfasının tüm rakamlarını birleşik servisten (UnifiedPortfolioService) okur.

BIST portföyü, BIST nakdi ve BIST dışı varlıklar tek TRY özetinde birleşir; sayfa TRY/USD gösterim anahtarı ve sınıf
sekmeleri sunar. Yalnızca veritabanından okunur (ağ çağrısı yok); fiyat yenileme `AssetsController` ve
`PriceRefreshController` tarafındadır, bu denetleyici `reload` ile yeniden okur.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.domain.market_clock import market_today
from src.domain.models.unified_portfolio import HUNDRED, UnifiedSummary
from src.ui_qml.controllers.portfolio_presenter import (
    TAB_ALL,
    TAB_KEYS,
    filter_rows,
    format_money,
    format_pct,
    slice_dict,
    tab_counts,
)
from src.ui_qml.models.holdings_list_model import HoldingsListModel

logger = logging.getLogger(__name__)

ZERO = Decimal("0")
SUPPORTED_CURRENCIES = ("TRY", "USD")


def _empty_summary(currency: str = "TRY") -> UnifiedSummary:
    return UnifiedSummary(
        holdings=(), cash_try=ZERO, total_value_try=ZERO, total_cost_try=ZERO, daily_gain_try=ZERO, slices=(),
        display_currency=currency,
    )


class MyPortfolioController(QObject):
    """QML context property: myPortfolioController"""

    summaryChanged = Signal()
    currencyChanged = Signal()
    tabChanged = Signal()

    def __init__(self, container=None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = getattr(container, "unified_portfolio_service", None) if container is not None else None
        self._calendar = getattr(container, "trading_calendar", None) if container is not None else None
        self._model = HoldingsListModel(self)
        self._currency = "TRY"
        self._tab = TAB_ALL
        self._summary: UnifiedSummary = _empty_summary()
        self.reload()

    # --- Okuma ---

    @Slot()
    def reload(self) -> None:
        """Birleşik özeti veritabanından yeniden okur; okunamazsa önceki özet korunur."""
        if self._service is not None:
            try:
                self._summary = self._service.get_summary(self._currency)
            except Exception as exc:
                logger.warning("Birleşik portföy özeti okunamadı: %s", exc)
        self._model.set_rows(filter_rows(self._summary, self._tab))
        self.summaryChanged.emit()

    @Slot()
    def reloadPrices(self) -> None:
        """`PriceRefreshController.pricesChanged` bağlantısı için ad takma adı."""
        self.reload()

    @Slot(str)
    def setDisplayCurrency(self, currency: str) -> None:
        code = (currency or "").strip().upper()
        if code not in SUPPORTED_CURRENCIES or code == self._currency:
            return
        self._currency = code
        self.reload()
        self.currencyChanged.emit()

    @Slot(str)
    def setActiveClass(self, tab_key: str) -> None:
        if tab_key not in TAB_KEYS or tab_key == self._tab:
            return
        self._tab = tab_key
        self._model.set_rows(filter_rows(self._summary, self._tab))
        self.tabChanged.emit()

    # --- Özellikler ---

    def _money(self, amount_try: Decimal) -> str:
        return format_money(self._summary.display_amount(amount_try), self._summary.display_currency)

    @Property(QObject, constant=True)
    def holdingsModel(self) -> HoldingsListModel:
        return self._model

    @Property(str, notify=currencyChanged)
    def displayCurrency(self) -> str:
        return self._currency

    @Property(bool, notify=summaryChanged)
    def displayUnavailable(self) -> bool:
        return self._summary.display_unavailable

    @Property(str, notify=tabChanged)
    def activeClass(self) -> str:
        return self._tab

    @Property(str, notify=summaryChanged)
    def totalValue(self) -> str:
        return self._money(self._summary.total_value_try)

    @Property(str, notify=summaryChanged)
    def totalCost(self) -> str:
        return self._money(self._summary.total_cost_try)

    @Property(str, notify=summaryChanged)
    def cashBalance(self) -> str:
        return self._money(self._summary.cash_try)

    @Property(str, notify=summaryChanged)
    def cashRatio(self) -> str:
        total = self._summary.total_value_try
        ratio = self._summary.cash_try / total * HUNDRED if total > 0 else ZERO
        return f"%{ratio:.1f}"

    @Property(str, notify=summaryChanged)
    def dailyGain(self) -> str:
        return self._money(self._summary.daily_gain_try)

    @Property(str, notify=summaryChanged)
    def dailyGainPct(self) -> str:
        return format_pct(self._summary.daily_change_pct)

    @Property(bool, notify=summaryChanged)
    def isMarketDayClosed(self) -> bool:
        """Bugün BIST işlem günü değil (hafta sonu/tatil): günlük K/Z son işlem gününün hareketidir."""
        calendar = self._calendar
        today = market_today()
        try:
            return not calendar.is_trading_day(today) if calendar is not None else today.weekday() >= 5
        except Exception:
            return today.weekday() >= 5

    @Property(bool, notify=summaryChanged)
    def isDailyPositive(self) -> bool:
        return self._summary.daily_gain_try >= 0

    @Property(str, notify=summaryChanged)
    def unrealizedPL(self) -> str:
        return self._money(self._summary.unrealized_pl_try)

    @Property(str, notify=summaryChanged)
    def unrealizedPLPct(self) -> str:
        return format_pct(self._summary.unrealized_pl_pct)

    @Property(bool, notify=summaryChanged)
    def isPLPositive(self) -> bool:
        return self._summary.unrealized_pl_try >= 0

    @Property(int, notify=summaryChanged)
    def holdingsCount(self) -> int:
        return len(self._summary.holdings)

    @Property(bool, notify=summaryChanged)
    def isPartial(self) -> bool:
        return self._summary.is_partial

    @Property("QVariantList", notify=summaryChanged)
    def unpricedSymbols(self) -> List[str]:
        return list(self._summary.unpriced_symbols)

    @Property("QVariantList", notify=summaryChanged)
    def staleSymbols(self) -> List[str]:
        """Fiyatı veya kuru güncel olmayan (eşikten eski) pozisyonlar."""
        return list(self._summary.stale_symbols)

    @Property(str, notify=summaryChanged)
    def usdRate(self) -> str:
        rate: Optional[Decimal] = self._summary.usd_try_rate
        return f"{rate:,.4f}" if rate is not None else "-"

    @Property("QVariantList", notify=summaryChanged)
    def allocationSlices(self) -> List[Dict[str, Any]]:
        return [slice_dict(item, self._summary) for item in self._summary.slices]

    @Property("QVariantMap", notify=summaryChanged)
    def tabCounts(self) -> Dict[str, int]:
        return tab_counts(self._summary)

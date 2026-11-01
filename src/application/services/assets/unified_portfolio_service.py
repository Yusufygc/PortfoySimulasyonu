from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Dict, List

from src.domain.models.unified_portfolio import (
    HUNDRED,
    ZERO,
    AllocationClass,
    AllocationSlice,
    HoldingValuation,
    UnifiedSummary,
)

SUPPORTED_DISPLAY_CURRENCIES = ("TRY", "USD")


class UnifiedPortfolioService:
    """BIST portföyü + BIST nakdi + varlık defterini tek TRY özetinde birleştirir (Portföyüm sayfası).

    Eksik fiyat veya kur sessizce atlanmaz: pozisyon TRY maliyetiyle değerlenir ve özet `is_partial` olur.
    Ana BIST hesapları (TWR, risk, optimizasyon) bu servisten etkilenmez.
    """

    def __init__(self, bist_reader, asset_reader, fx_rate_service) -> None:
        self._bist_reader = bist_reader
        self._asset_reader = asset_reader
        self._fx = fx_rate_service

    def get_summary(self, display_currency: str = "TRY") -> UnifiedSummary:
        currency = (display_currency or "TRY").strip().upper()
        if currency not in SUPPORTED_DISPLAY_CURRENCIES:
            raise ValueError(f"Desteklenmeyen gösterim para birimi: {display_currency}")

        bist_holdings, cash = self._bist_reader.read()
        holdings = bist_holdings + self._asset_reader.read()
        total_value = sum((h.value_try for h in holdings), ZERO) + cash
        weighted = sorted((self._with_weight(h, total_value) for h in holdings), key=lambda h: h.value_try, reverse=True)

        display = self._display(currency)
        return UnifiedSummary(
            holdings=tuple(weighted),
            cash_try=cash,
            total_value_try=total_value,
            total_cost_try=sum((h.cost_try for h in holdings), ZERO),
            daily_gain_try=sum((h.daily_gain_try for h in holdings), ZERO),
            slices=tuple(self._slices(weighted, cash, total_value)),
            unpriced_symbols=tuple(h.symbol for h in weighted if not h.is_priced),
            **display,
        )

    @staticmethod
    def _with_weight(holding: HoldingValuation, total_value: Decimal) -> HoldingValuation:
        weight = holding.value_try / total_value * HUNDRED if total_value > 0 else ZERO
        return replace(holding, weight_pct=weight)

    @staticmethod
    def _slices(holdings: List[HoldingValuation], cash: Decimal, total_value: Decimal) -> List[AllocationSlice]:
        values: Dict[AllocationClass, Decimal] = {}
        counts: Dict[AllocationClass, int] = {}
        for holding in holdings:
            values[holding.allocation_class] = values.get(holding.allocation_class, ZERO) + holding.value_try
            counts[holding.allocation_class] = counts.get(holding.allocation_class, 0) + 1
        if cash > 0:
            values[AllocationClass.CASH] = cash
            counts[AllocationClass.CASH] = 0
        slices = [
            AllocationSlice(
                allocation_class=cls,
                value_try=value,
                weight_pct=value / total_value * HUNDRED if total_value > 0 else ZERO,
                holdings_count=counts[cls],
            )
            for cls, value in values.items()
            if value > 0
        ]
        return sorted(slices, key=lambda s: s.value_try, reverse=True)

    def _display(self, currency: str) -> dict:
        if currency == "TRY":
            return {"display_currency": "TRY", "display_rate": Decimal("1")}
        usd_try = self._fx.get_rate("USD", "TRY")
        if usd_try is None:
            return {"display_currency": "TRY", "display_rate": Decimal("1"), "display_unavailable": True}
        return {"display_currency": "USD", "display_rate": Decimal("1") / usd_try, "usd_try_rate": usd_try}

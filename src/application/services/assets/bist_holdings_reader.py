from __future__ import annotations

from decimal import Decimal
from typing import List, Tuple

from src.domain.models.unified_portfolio import AllocationClass, HoldingValuation, daily_gain


class BistHoldingsReader:
    """BIST portföyünün açık pozisyonlarını TRY değerlemesine çevirir (mevcut BIST servislerinden okur).

    Güncel fiyat `CurrentPriceResolver` ile (canlı fiyat yalnızca geçerliyse, aksi halde son kapanış) çözülür.
    Fiyatı çözülemeyen pozisyon maliyetiyle değerlenir ve `is_priced=False` işaretlenir.
    """

    def __init__(self, portfolio_service, stock_lookup_service, price_resolver) -> None:
        self._portfolio_service = portfolio_service
        self._stock_lookup = stock_lookup_service
        self._resolver = price_resolver

    def read(self) -> Tuple[List[HoldingValuation], Decimal]:
        """(pozisyon değerlemeleri, BIST TRY nakit bakiyesi)"""
        cash = Decimal(str(self._portfolio_service.get_cash_balance() or 0))
        active = self._portfolio_service.get_current_portfolio().active_positions
        if not active:
            return [], cash

        stock_ids = list(active)
        stocks = self._stock_lookup.get_stocks(stock_ids)
        resolved = self._resolver.resolve(stock_ids)
        holdings = [
            self._valuate(stock_id, position, stocks.get(stock_id), resolved.get(stock_id))
            for stock_id, position in active.items()
        ]
        return holdings, cash

    def _valuate(self, stock_id, position, stock, resolved) -> HoldingValuation:
        symbol = (stock.ticker if stock else f"STOCK_{stock_id}").replace(".IS", "").strip().upper()
        name = (stock.name if stock and stock.name else symbol).replace(".IS", "").strip()
        cost = position.total_cost
        base = dict(
            key=f"{AllocationClass.BIST_STOCK.value}:{symbol}",
            symbol=symbol,
            name=name,
            allocation_class=AllocationClass.BIST_STOCK,
            quantity=Decimal(position.total_quantity),
            native_currency="TRY",
            cost_native=cost,
            cost_try=cost,
        )
        if resolved is None:
            return HoldingValuation(**base, value_try=cost, is_priced=False)

        value = position.market_value(resolved.price)
        change = self._resolver.daily_change_pct(stock_id, resolved)
        return HoldingValuation(
            **base,
            value_try=value,
            price_native=resolved.price,
            value_native=value,
            daily_change_pct=change,
            daily_gain_try=daily_gain(value, change),
        )


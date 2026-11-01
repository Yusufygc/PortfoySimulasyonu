# src/domain/models/asset_position.py

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from decimal import Decimal
from typing import Dict, Iterable, List, Optional

from .asset_trade import AssetTrade
from .trade import TradeSide


@dataclass
class AssetPosition:
    """
    Tek bir varlık için eldeki pozisyon (ağırlıklı ortalama maliyet, `Position` ile aynı mantık, Decimal miktar).

    - total_cost: eldeki miktarın maliyeti, varlığın para biriminde
    - total_cost_try: aynı maliyet, her alımın kendi işlem kuruyla TRY
    - realized_pl / realized_pl_try: satışlarla kilitlenen kâr/zarar
    """

    asset_id: int
    trades: List[AssetTrade] = field(default_factory=list)
    total_quantity: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")
    total_cost_try: Decimal = Decimal("0")
    realized_pl: Decimal = Decimal("0")
    realized_pl_try: Decimal = Decimal("0")

    @property
    def is_open(self) -> bool:
        return self.total_quantity > 0

    @property
    def average_cost(self) -> Optional[Decimal]:
        if self.total_quantity == 0:
            return None
        return self.total_cost / self.total_quantity

    def market_value(self, current_price: Decimal) -> Decimal:
        return current_price * self.total_quantity

    def unrealized_pl(self, current_price: Decimal) -> Decimal:
        return self.market_value(current_price) - self.total_cost

    @classmethod
    def from_trades(cls, asset_id: int, trades: Iterable[AssetTrade], is_sorted: bool = False) -> "AssetPosition":
        position = cls(asset_id=asset_id)
        ordered = trades if is_sorted else sorted(trades, key=_trade_order_key)
        for trade in ordered:
            position.apply_trade(trade)
        return position

    def apply_trade(self, trade: AssetTrade) -> None:
        if trade.asset_id != self.asset_id:
            raise ValueError("Trade asset_id does not match AssetPosition asset_id")

        if trade.side == TradeSide.BUY:
            self._apply_buy(trade)
        elif trade.side == TradeSide.SELL:
            self._apply_sell(trade)
        else:
            raise ValueError(f"Unknown trade side: {trade.side}")

        self.trades.append(trade)

    def _apply_buy(self, trade: AssetTrade) -> None:
        self.total_cost += trade.cash_amount          # ücret maliyete dahildir
        self.total_cost_try += trade.cash_amount * trade.fx_rate_to_try
        self.total_quantity += trade.quantity

    def _apply_sell(self, trade: AssetTrade) -> None:
        if trade.quantity > self.total_quantity:
            raise ValueError("Cannot sell more than current position quantity")

        sold_ratio = trade.quantity / self.total_quantity
        cost_of_sold = self.total_cost * sold_ratio
        cost_of_sold_try = self.total_cost_try * sold_ratio

        self.realized_pl += trade.cash_amount - cost_of_sold              # net gelir (ücret düşülmüş)
        self.realized_pl_try += trade.cash_amount * trade.fx_rate_to_try - cost_of_sold_try

        self.total_quantity -= trade.quantity
        self.total_cost -= cost_of_sold
        self.total_cost_try -= cost_of_sold_try

        if self.total_quantity == 0:
            self.total_cost = Decimal("0")
            self.total_cost_try = Decimal("0")


def _trade_order_key(trade: AssetTrade):
    return (trade.trade_date, trade.trade_time or time.min, trade.id or 0)


@dataclass
class AssetLedger:
    """Varlık defteri: işlem geçmişinden yeniden hesaplanır (event-sourced); türev değer saklanmaz."""

    positions: Dict[int, AssetPosition] = field(default_factory=dict)

    @classmethod
    def from_trades(cls, trades: Iterable[AssetTrade]) -> "AssetLedger":
        ledger = cls()
        for trade in sorted(trades, key=_trade_order_key):
            position = ledger.positions.get(trade.asset_id)
            if position is None:
                position = AssetPosition(asset_id=trade.asset_id)
                ledger.positions[trade.asset_id] = position
            position.apply_trade(trade)
        return ledger

    def get_position(self, asset_id: int) -> Optional[AssetPosition]:
        return self.positions.get(asset_id)

    def open_positions(self) -> List[AssetPosition]:
        return [position for position in self.positions.values() if position.is_open]

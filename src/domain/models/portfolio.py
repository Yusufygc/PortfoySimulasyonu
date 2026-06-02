# src/domain/models/portfolio.py

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import time
from decimal import Decimal

from typing import Dict, Iterable, List, Mapping

from .position import Position
from .trade import Trade


@dataclass
class Portfolio:
    """
    Tüm portföyü temsil eder.
    Birden fazla Position (her biri bir hisse) içerir.
    """
    positions: Dict[int, Position] = field(default_factory=dict)  # key: stock_id

    # --------- Pozisyon erişimi --------- #

    @property
    def active_positions(self) -> Dict[int, Position]:
        """Sıfırdan büyük lot'u olan açık pozisyonlar. Tam satılan hisseler dahil değil."""
        return {sid: p for sid, p in self.positions.items() if p.total_quantity > 0}

    def get_position(self, stock_id: int) -> Position:
        """
        Hisse için pozisyonu döner; yoksa sıfırdan oluşturur.
        """
        if stock_id not in self.positions:
            self.positions[stock_id] = Position(stock_id=stock_id)
        return self.positions[stock_id]

    # --------- Trade ekleme --------- #

    def apply_trade(self, trade: Trade) -> None:
        """
        Tek bir trade'i ilgili pozisyona uygular.
        Application/service katmanı DB'ye kaydetmeden önce veya sonra çağırabilir.
        """
        position = self.get_position(trade.stock_id)
        position.apply_trade(trade)

    @classmethod
    def from_trades(cls, trades: Iterable[Trade], is_sorted: bool = False) -> "Portfolio":
        """
        Tüm trades listesinden portföyü oluşturur.
        Genelde repository'den 'tüm trade'ler' çekilip burada domain'e dökülür.
        """
        portfolio = cls()
        
        ordered_trades = trades if is_sorted else sorted(
            trades,
            key=lambda t: (
                t.trade_date,
                t.trade_time if t.trade_time is not None else time.min,
                getattr(t, "id", 0) or 0,
            ),
        )
        
        for trade in ordered_trades:
            portfolio.apply_trade(trade)
        return portfolio

    # --------- Portföy değeri & P&L hesapları --------- #

    def total_cost(self) -> Decimal:
        """
        Portföydeki tüm açık pozisyonların toplam maliyeti.
        """
        return sum((p.total_cost for p in self.positions.values()), Decimal("0"))

    def total_realized_pl(self) -> Decimal:
        """
        Tüm hisseler için gerçekleşmiş kar/zarar toplamı.
        """
        return sum((p.realized_pl for p in self.positions.values()), Decimal("0"))

    def total_market_value(self, price_map: Mapping[int, Decimal]) -> Decimal:
        """
        Güncel fiyatlara göre portföyün toplam piyasa değeri.
        price_map: { stock_id: current_price }
        """
        total = Decimal("0")
        for stock_id, position in self.positions.items():
            current_price = price_map.get(stock_id)
            if current_price is None:
                continue
            total += position.market_value(current_price)
        return total

    def total_unrealized_pl(self, price_map: Mapping[int, Decimal]) -> Decimal:
        """
        Tüm hisseler için gerçekleşmemiş kar/zarar toplamı.
        """
        total = Decimal("0")
        for stock_id, position in self.positions.items():
            current_price = price_map.get(stock_id)
            if current_price is None:
                continue
            total += position.unrealized_pl(current_price)
        return total

    # --------- UI için basit özet/dto çıkarma --------- #

    def to_summary_dict(
        self, price_map: Mapping[int, Decimal]
    ) -> Dict[str, Decimal]:
        """
        UI veya servis katmanı için basit bir özet sözlük.
        """
        total_cost = self.total_cost()
        total_value = self.total_market_value(price_map)
        total_unrealized = self.total_unrealized_pl(price_map)
        total_realized = self.total_realized_pl()

        return {
            "total_cost": total_cost,
            "total_value": total_value,
            "total_unrealized_pl": total_unrealized,
            "total_realized_pl": total_realized,
        }

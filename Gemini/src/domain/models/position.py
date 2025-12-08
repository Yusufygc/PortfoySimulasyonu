# src/domain/models/position.py

from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterable, List, Optional

from .trade import Trade, TradeSide


@dataclass
class Position:
    """
    Tek bir hisse için portföydeki pozisyonu temsil eder.

    - total_quantity: eldeki toplam lot
    - total_cost: eldeki lotların maliyet toplamı (gerçekleşmemiş kısım)
    - realized_pl: gerçekleşmiş kar/zarar (satışlarla kilitlenen)
    """
    stock_id: int
    trades: List[Trade] = field(default_factory=list)
    total_quantity: int = 0
    total_cost: Decimal = Decimal("0")
    realized_pl: Decimal = Decimal("0")

    # --------- Temel hesaplamalar --------- #

    @property
    def average_cost(self) -> Optional[Decimal]:
        """
        Elde lot varsa ortalama maliyet = total_cost / total_quantity.
        Eğer pozisyon tamamen kapanmışsa None dönebilir.
        """
        if self.total_quantity == 0:
            return None
        return self.total_cost / Decimal(self.total_quantity)

    def market_value(self, current_price: Decimal) -> Decimal:
        """
        Güncel fiyata göre pozisyonun piyasa değeri.
        """
        return current_price * Decimal(self.total_quantity)

    def unrealized_pl(self, current_price: Decimal) -> Decimal:
        """
        Gerçekleşmemiş kar/zarar = market_value - total_cost.
        (Sadece eldeki açık pozisyon için.)
        """
        return self.market_value(current_price) - self.total_cost

    # --------- Pozisyonu trade'lerden oluşturma / güncelleme --------- #

    @classmethod
    def from_trades(cls, stock_id: int, trades: Iterable[Trade]) -> "Position":
        """
        Aynı hisseye ait tüm trade'leri alıp pozisyonu baştan hesaplar.
        (DB'den çekilen datayı Domain'e çevirirken kullanışlı.)
        """
        position = cls(stock_id=stock_id)

        for trade in sorted(trades, key=lambda t: (t.trade_date, t.trade_time or 0)):
            position.apply_trade(trade)

        return position

    def apply_trade(self, trade: Trade) -> None:
        """
        Tek bir trade'i mevcut pozisyona uygular.
        İş kuralı:
            - BUY: total_quantity & total_cost artar
            - SELL: önce gerçekleşen kar/zarar hesaplanır, sonra quantity & cost azaltılır
        """
        if trade.stock_id != self.stock_id:
            raise ValueError("Trade stock_id does not match Position stock_id")

        self.trades.append(trade)

        if trade.side == TradeSide.BUY:
            self._apply_buy(trade)
        elif trade.side == TradeSide.SELL:
            self._apply_sell(trade)
        else:
            raise ValueError(f"Unknown trade side: {trade.side}")

    def _apply_buy(self, trade: Trade) -> None:
        """
        Alış işlemi pozisyona eklenir.
        Weighted average cost hesabı:
            yeni_total_cost = eski_total_cost + (quantity * price)
            yeni_total_quantity = eski_quantity + quantity
        """
        trade_total = trade.total_amount
        self.total_cost += trade_total
        self.total_quantity += trade.quantity

    def _apply_sell(self, trade: Trade) -> None:
        """
        Satış işlemi:
            - Eldeki lottan düşer
            - Gerçekleşmiş kar/zararı hesaplar (FIFO yerine ortalama maliyet varsayıyoruz)
        """
        if trade.quantity > self.total_quantity:
            # Uygulama servisinin de önceden kontrol etmesi gerekir ama
            # domain'de de guard olsun.
            raise ValueError("Cannot sell more than current position quantity")

        avg_cost = self.average_cost or Decimal("0")
        sell_proceeds = trade.total_amount       # satış tutarı
        cost_of_sold = avg_cost * Decimal(trade.quantity)

        realized = sell_proceeds - cost_of_sold
        self.realized_pl += realized

        # Maliyet ve quantity azalt
        self.total_quantity -= trade.quantity
        self.total_cost -= cost_of_sold

        # Pozisyon tamamen kapanmışsa çok küçük floating hataları toparlamak için:
        if self.total_quantity == 0:
            self.total_cost = Decimal("0")

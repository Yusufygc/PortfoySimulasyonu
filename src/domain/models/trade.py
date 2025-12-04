# src/domain/models/trade.py

from __future__ import annotations
from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal
from enum import Enum
from typing import Optional


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class Trade:
    """
    Tek bir alım/satım işlemini temsil eder.
    DB'deki trades tablosunun domain karşılığıdır.
    """
    id: Optional[int]
    stock_id: int
    trade_date: date
    trade_time: Optional[time]
    side: TradeSide
    quantity: int          # lot sayısı
    price: Decimal         # birim fiyat

    @property
    def total_amount(self) -> Decimal:
        """
        İşlemin toplam tutarı = quantity * price
        Not: SELL işlemlerinde de pozitif tutulur, iş kuralı tarafında yorumlanır.
        """
        return self.price * Decimal(self.quantity)

    # ---- Factory / yardımcı metotlar (İstersen kullanırsın) ---- #

    @classmethod
    def create_buy(
        cls,
        stock_id: int,
        trade_date: date,
        quantity: int,
        price: Decimal,
        trade_time: Optional[time] = None,
    ) -> "Trade":
        """
        Yeni bir alış işlemi oluşturur (id henüz yok, DB insert sonrası gelir).
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive for BUY trades")

        if price <= 0:
            raise ValueError("Price must be positive")

        return cls(
            id=None,
            stock_id=stock_id,
            trade_date=trade_date,
            trade_time=trade_time,
            side=TradeSide.BUY,
            quantity=quantity,
            price=price,
        )

    @classmethod
    def create_sell(
        cls,
        stock_id: int,
        trade_date: date,
        quantity: int,
        price: Decimal,
        trade_time: Optional[time] = None,
    ) -> "Trade":
        """
        Yeni bir satış işlemi oluşturur.
        Quantity yine pozitif girilir; BUY/SELL ayrımını side üzerinden yapıyoruz.
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive for SELL trades")

        if price <= 0:
            raise ValueError("Price must be positive")

        return cls(
            id=None,
            stock_id=stock_id,
            trade_date=trade_date,
            trade_time=trade_time,
            side=TradeSide.SELL,
            quantity=quantity,
            price=price,
        )

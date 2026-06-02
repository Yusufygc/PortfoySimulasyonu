# src/domain/models/model_portfolio.py

from __future__ import annotations
from dataclasses import dataclass
from datetime import date, time, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class ModelTradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class ModelPortfolio:
    """
    Model portföy bilgilerini temsil eder.
    'model_portfolios' tablosunun domain karşılığı.
    """
    id: Optional[int]
    name: str
    description: Optional[str] = None
    initial_cash: Decimal = Decimal("100000.00")
    sort_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass(frozen=True)
class ModelPortfolioTrade:
    """
    Model portföy içindeki bir alım/satım işlemini temsil eder.
    'model_portfolio_trades' tablosunun domain karşılığı.
    """
    id: Optional[int]
    portfolio_id: int
    stock_id: int
    trade_date: date
    trade_time: Optional[time]
    side: ModelTradeSide
    quantity: int          # lot sayısı
    price: Decimal         # birim fiyat
    created_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not isinstance(self.side, ModelTradeSide):
            try:
                object.__setattr__(self, "side", ModelTradeSide(self.side))
            except ValueError as exc:
                raise ValueError(f"Unknown model trade side: {self.side}") from exc

        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")

        if self.price <= 0:
            raise ValueError("Price must be positive")

    @property
    def total_amount(self) -> Decimal:
        """
        İşlemin toplam tutarı = quantity * price
        """
        return self.price * Decimal(self.quantity)

    @classmethod
    def create_buy(
        cls,
        portfolio_id: int,
        stock_id: int,
        trade_date: date,
        quantity: int,
        price: Decimal,
        trade_time: Optional[time] = None,
    ) -> "ModelPortfolioTrade":
        """
        Yeni bir alış işlemi oluşturur.
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive for BUY trades")

        if price <= 0:
            raise ValueError("Price must be positive")

        return cls(
            id=None,
            portfolio_id=portfolio_id,
            stock_id=stock_id,
            trade_date=trade_date,
            trade_time=trade_time,
            side=ModelTradeSide.BUY,
            quantity=quantity,
            price=price,
        )

    @classmethod
    def create_sell(
        cls,
        portfolio_id: int,
        stock_id: int,
        trade_date: date,
        quantity: int,
        price: Decimal,
        trade_time: Optional[time] = None,
    ) -> "ModelPortfolioTrade":
        """
        Yeni bir satış işlemi oluşturur.
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive for SELL trades")

        if price <= 0:
            raise ValueError("Price must be positive")

        return cls(
            id=None,
            portfolio_id=portfolio_id,
            stock_id=stock_id,
            trade_date=trade_date,
            trade_time=trade_time,
            side=ModelTradeSide.SELL,
            quantity=quantity,
            price=price,
        )

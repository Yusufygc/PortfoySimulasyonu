# src/domain/models/model_portfolio.py

from __future__ import annotations
from dataclasses import dataclass
from datetime import date, time, datetime
from decimal import Decimal
from enum import Enum
from typing import NamedTuple, Optional


class ModelPortfolioTradeSpec(NamedTuple):
    portfolio_id: int
    stock_id: int
    trade_date: date
    quantity: int
    price: Decimal
    trade_time: Optional[time] = None


class ModelTradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class ModelPortfolioCashMovementType(str, Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"


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
    def create_buy(cls, spec: "ModelPortfolioTradeSpec") -> "ModelPortfolioTrade":
        if spec.quantity <= 0:
            raise ValueError("Quantity must be positive for BUY trades")
        if spec.price <= 0:
            raise ValueError("Price must be positive")
        return cls(
            id=None,
            portfolio_id=spec.portfolio_id,
            stock_id=spec.stock_id,
            trade_date=spec.trade_date,
            trade_time=spec.trade_time,
            side=ModelTradeSide.BUY,
            quantity=spec.quantity,
            price=spec.price,
        )

    @classmethod
    def create_sell(cls, spec: "ModelPortfolioTradeSpec") -> "ModelPortfolioTrade":
        if spec.quantity <= 0:
            raise ValueError("Quantity must be positive for SELL trades")
        if spec.price <= 0:
            raise ValueError("Price must be positive")
        return cls(
            id=None,
            portfolio_id=spec.portfolio_id,
            stock_id=spec.stock_id,
            trade_date=spec.trade_date,
            trade_time=spec.trade_time,
            side=ModelTradeSide.SELL,
            quantity=spec.quantity,
            price=spec.price,
        )


@dataclass(frozen=True)
class ModelPortfolioCashMovement:
    id: Optional[int]
    portfolio_id: int
    movement_date: date
    movement_time: Optional[time]
    type: ModelPortfolioCashMovementType
    amount: Decimal
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not isinstance(self.type, ModelPortfolioCashMovementType):
            try:
                object.__setattr__(self, "type", ModelPortfolioCashMovementType(self.type))
            except ValueError as exc:
                raise ValueError(f"Unknown model portfolio cash movement type: {self.type}") from exc
        if self.amount <= 0:
            raise ValueError("Cash movement amount must be positive")

    @classmethod
    def create_deposit(
        cls,
        portfolio_id: int,
        amount: Decimal,
        movement_date: date,
        movement_time: Optional[time] = None,
        notes: Optional[str] = None,
    ) -> "ModelPortfolioCashMovement":
        return cls(
            id=None,
            portfolio_id=portfolio_id,
            movement_date=movement_date,
            movement_time=movement_time,
            type=ModelPortfolioCashMovementType.DEPOSIT,
            amount=amount,
            notes=notes,
        )

    @classmethod
    def create_withdraw(
        cls,
        portfolio_id: int,
        amount: Decimal,
        movement_date: date,
        movement_time: Optional[time] = None,
        notes: Optional[str] = None,
    ) -> "ModelPortfolioCashMovement":
        return cls(
            id=None,
            portfolio_id=portfolio_id,
            movement_date=movement_date,
            movement_time=movement_time,
            type=ModelPortfolioCashMovementType.WITHDRAW,
            amount=amount,
            notes=notes,
        )

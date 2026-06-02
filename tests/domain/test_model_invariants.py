from datetime import date
from decimal import Decimal

import pytest

from src.domain.models.cash_movement import CashMovement, CashMovementType
from src.domain.models.corporate_action import ActionType, CorporateAction
from src.domain.models.model_portfolio import ModelPortfolioTrade, ModelTradeSide
from src.domain.models.trade import Trade, TradeSide


def test_trade_constructor_rejects_invalid_values():
    with pytest.raises(ValueError, match="Quantity"):
        Trade(
            id=None,
            stock_id=1,
            trade_date=date(2026, 1, 1),
            trade_time=None,
            side=TradeSide.BUY,
            quantity=0,
            price=Decimal("10"),
        )

    with pytest.raises(ValueError, match="Price"):
        Trade(
            id=None,
            stock_id=1,
            trade_date=date(2026, 1, 1),
            trade_time=None,
            side=TradeSide.BUY,
            quantity=1,
            price=Decimal("-1"),
        )


def test_trade_constructor_allows_zero_price_for_synthetic_actions():
    trade = Trade(
        id=None,
        stock_id=1,
        trade_date=date(2026, 1, 1),
        trade_time=None,
        side="BUY",
        quantity=1,
        price=Decimal("0"),
    )

    assert trade.side == TradeSide.BUY
    assert trade.total_amount == Decimal("0")


def test_cash_movement_constructor_rejects_invalid_values():
    with pytest.raises(ValueError):
        CashMovement(
            id=None,
            movement_date=date(2026, 1, 1),
            movement_time=None,
            type=CashMovementType.DEPOSIT,
            amount=Decimal("0"),
        )

    with pytest.raises(ValueError, match="Unknown"):
        CashMovement(
            id=None,
            movement_date=date(2026, 1, 1),
            movement_time=None,
            type="INVALID",
            amount=Decimal("1"),
        )


def test_model_portfolio_trade_constructor_rejects_invalid_values():
    with pytest.raises(ValueError, match="Quantity"):
        ModelPortfolioTrade(
            id=None,
            portfolio_id=1,
            stock_id=1,
            trade_date=date(2026, 1, 1),
            trade_time=None,
            side=ModelTradeSide.BUY,
            quantity=0,
            price=Decimal("10"),
        )

    trade = ModelPortfolioTrade(
        id=None,
        portfolio_id=1,
        stock_id=1,
        trade_date=date(2026, 1, 1),
        trade_time=None,
        side="SELL",
        quantity=1,
        price=Decimal("10"),
    )

    assert trade.side == ModelTradeSide.SELL


def test_corporate_action_constructor_rejects_invalid_values():
    with pytest.raises(ValueError, match="ratio"):
        CorporateAction(
            id=None,
            stock_id=1,
            action_type=ActionType.BEDELSIZ,
            ex_date=date(2026, 1, 1),
            ratio=Decimal("0"),
            subscription_price=None,
            announcement_date=None,
            notes=None,
            applied=False,
        )

    with pytest.raises(ValueError, match="Subscription"):
        CorporateAction(
            id=None,
            stock_id=1,
            action_type=ActionType.BEDELLI,
            ex_date=date(2026, 1, 1),
            ratio=Decimal("0.50"),
            subscription_price=None,
            announcement_date=None,
            notes=None,
            applied=False,
        )

    action = CorporateAction(
        id=None,
        stock_id=1,
        action_type="BEDELSIZ",
        ex_date=date(2026, 1, 1),
        ratio=Decimal("0.50"),
        subscription_price=None,
        announcement_date=None,
        notes=None,
        applied=False,
    )

    assert action.action_type == ActionType.BEDELSIZ

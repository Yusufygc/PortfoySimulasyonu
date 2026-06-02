from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Iterable

from src.domain.models.corporate_action import ActionType, CorporateAction
from src.domain.ports.repositories.i_corporate_action_repo import ICorporateActionRepository
from src.domain.ports.repositories.i_price_repo import IPriceRepository


@dataclass(frozen=True)
class PriceAdjustmentResult:
    action_id: int
    stock_id: int
    factor: Decimal
    adjusted_count: int
    already_adjusted: bool = False


def calculate_price_adjustment_factor(
    action: CorporateAction,
    previous_close: Decimal | None = None,
) -> Decimal:
    if action.action_type == ActionType.BEDELSIZ:
        return Decimal("1") / (Decimal("1") + action.ratio)

    if previous_close is None or previous_close <= 0:
        raise ValueError("Bedelli fiyat duzeltmesi icin ex-date oncesi kapanis fiyati gereklidir.")

    subscription_price = action.subscription_price
    if subscription_price is None:
        raise ValueError("Bedelli fiyat duzeltmesi icin kullanim fiyati gereklidir.")

    return (previous_close + action.ratio * subscription_price) / (
        (Decimal("1") + action.ratio) * previous_close
    )


def cumulative_adjustment_factor(actions: Iterable[CorporateAction], price_date) -> Decimal:
    factor = Decimal("1")
    for action in actions:
        if not action.applied or not action.prices_adjusted:
            continue
        if action.price_adjustment_factor is None:
            continue
        if price_date < action.ex_date:
            factor *= action.price_adjustment_factor
    return factor


def adjusted_market_price(
    close_price: Decimal | int | float | str,
    price_date,
    actions: Iterable[CorporateAction],
) -> Decimal:
    value = close_price if isinstance(close_price, Decimal) else Decimal(str(close_price))
    return value * cumulative_adjustment_factor(actions, price_date)


class CorporateActionPriceAdjustmentService:
    def __init__(
        self,
        action_repo: ICorporateActionRepository,
        price_repo: IPriceRepository,
    ) -> None:
        self._action_repo = action_repo
        self._price_repo = price_repo

    def adjust_prices_for_action(self, action_id: int) -> PriceAdjustmentResult:
        action = self._action_repo.get_by_id(action_id)
        if action is None:
            raise ValueError(f"Kurumsal islem bulunamadi: id={action_id}")
        if not action.applied:
            raise ValueError("Fiyat gecmisi duzeltmeden once kurumsal islem portfoye uygulanmalidir.")
        return self.adjust_prices_for_applied_action(action)

    def adjust_prices_for_applied_action(self, action: CorporateAction) -> PriceAdjustmentResult:
        if action.id is None:
            raise ValueError("Fiyat duzeltmesi icin kurumsal islem id degeri gereklidir.")
        if action.prices_adjusted:
            return PriceAdjustmentResult(
                action_id=action.id,
                stock_id=action.stock_id,
                factor=action.price_adjustment_factor or Decimal("1"),
                adjusted_count=action.price_adjustment_count,
                already_adjusted=True,
            )

        factor = self._factor_for_action(action)
        adjusted_count = self._price_repo.adjust_prices_before_date(
            stock_id=action.stock_id,
            before_date=action.ex_date,
            factor=factor,
        )
        self._action_repo.mark_prices_adjusted(action.id, factor, adjusted_count)
        return PriceAdjustmentResult(
            action_id=action.id,
            stock_id=action.stock_id,
            factor=factor,
            adjusted_count=adjusted_count,
        )

    def _factor_for_action(self, action: CorporateAction) -> Decimal:
        if action.action_type == ActionType.BEDELSIZ:
            return calculate_price_adjustment_factor(action)

        previous_price_date = action.ex_date - timedelta(days=1)
        previous_daily = self._price_repo.get_last_price_before(action.stock_id, previous_price_date)
        previous_close = previous_daily.close_price if previous_daily else None
        return calculate_price_adjustment_factor(action, previous_close)

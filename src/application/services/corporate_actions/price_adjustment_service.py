from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta, datetime
from decimal import Decimal
from typing import Iterable, Dict

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


def _filter_applied_actions(actions: Iterable[CorporateAction]) -> list:
    return sorted(
        [a for a in actions if a.applied and a.prices_adjusted],
        key=lambda a: a.ex_date,
        reverse=True,
    )


def _to_decimal_dict(series: Dict[date, Decimal]) -> Dict[date, Decimal]:
    return {k: (v if isinstance(v, Decimal) else Decimal(str(v))) for k, v in series.items()}


def _find_download_transition_date(sorted_dates, adjusted_series, action, factor) -> "date | None":
    target_ratio = Decimal("1") / factor
    for i in range(len(sorted_dates) - 1):
        d, d_next = sorted_dates[i], sorted_dates[i + 1]
        if abs((d_next - action.ex_date).days) > 7:
            continue
        p, p_next = adjusted_series[d], adjusted_series[d_next]
        if p <= 0 or p_next <= 0:
            continue
        if abs(p / p_next - target_ratio) / target_ratio < Decimal("0.15"):
            return d_next
    return None


def _apply_action_adjustments(sorted_dates, adjusted_series, action, factor) -> None:
    transition_date = _find_download_transition_date(sorted_dates, adjusted_series, action, factor)
    if transition_date is not None:
        for d in sorted_dates:
            if d < transition_date:
                adjusted_series[d] = adjusted_series[d] * factor
    else:
        if sorted_dates[-1] < action.ex_date:
            for d in sorted_dates:
                adjusted_series[d] = adjusted_series[d] * factor


def adjust_downloaded_series(
    series: Dict[date, Decimal],
    actions: Iterable[CorporateAction],
) -> Dict[date, Decimal]:
    """
    Downloads raw series and adjusts for applied corporate actions,
    avoiding double-adjusting if the series is already adjusted in Yahoo Finance.
    """
    if not series or not actions:
        return series
    sorted_actions = _filter_applied_actions(actions)
    if not sorted_actions:
        return series
    adjusted_series = _to_decimal_dict(series)
    sorted_dates = sorted(adjusted_series.keys())
    for action in sorted_actions:
        factor = action.price_adjustment_factor
        if factor is None or factor == Decimal("1"):
            continue
        _apply_action_adjustments(sorted_dates, adjusted_series, action, factor)
    return adjusted_series


def _find_price_transition_date(db_prices_sorted, action, factor):
    for i in range(len(db_prices_sorted) - 1):
        dp1 = db_prices_sorted[i]
        dp2 = db_prices_sorted[i + 1]
        if abs((dp2.price_date - action.ex_date).days) > 7:
            continue
        if dp1.close_price <= 0 or dp2.close_price <= 0:
            continue
        r = dp1.close_price / dp2.close_price
        target_ratio = Decimal("1") / factor
        if abs(r - target_ratio) / target_ratio < Decimal("0.15"):
            return dp2.price_date
    return None


def _suggests_early_adjust(p_before: Decimal, p_after: Decimal, factor: Decimal) -> bool:
    if not (p_before > 0 and p_after > 0):
        return False
    r = p_before / p_after
    target_ratio = Decimal("1") / factor
    return target_ratio > Decimal("1.3") and r < Decimal("1.3")


def _determine_adjust_before_date(db_prices_sorted, action, factor, transition_date):
    if transition_date is not None:
        return transition_date
    prices_before = [dp for dp in db_prices_sorted if dp.price_date < action.ex_date]
    prices_after = [dp for dp in db_prices_sorted if dp.price_date >= action.ex_date]
    if prices_before and prices_after:
        if _suggests_early_adjust(prices_before[-1].close_price, prices_after[0].close_price, factor):
            return date(2000, 1, 1)
    return action.ex_date


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
        start_search = action.ex_date - timedelta(days=10)
        end_search = action.ex_date + timedelta(days=10)
        db_prices = self._price_repo.get_price_series(action.stock_id, start_search, end_search)
        db_prices_sorted = sorted(db_prices, key=lambda dp: dp.price_date)
        transition_date = _find_price_transition_date(db_prices_sorted, action, factor)
        before_date = _determine_adjust_before_date(db_prices_sorted, action, factor, transition_date)
        adjusted_count = self._price_repo.adjust_prices_before_date(
            stock_id=action.stock_id,
            before_date=before_date,
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


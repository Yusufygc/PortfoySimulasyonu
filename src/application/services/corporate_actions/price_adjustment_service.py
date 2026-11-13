from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import timedelta
from decimal import Decimal

from src.domain.models.corporate_action import ActionType, CorporateAction
from src.domain.ports.repositories.i_corporate_action_repo import ICorporateActionRepository
from src.domain.ports.repositories.i_price_repo import IPriceRepository


logger = logging.getLogger(__name__)


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


class CorporateActionPriceAdjustmentService:
    def __init__(
        self,
        action_repo: ICorporateActionRepository,
        price_repo: IPriceRepository,
        stock_repo=None,
        market_action_service=None,
        projection=None,
    ) -> None:
        """`price_repo` yalnızca bedelli faktörü için ex-date öncesi kapanışı okur; `projection`
        (PriceProjectionService) SQLite yansımasını yeniler."""
        self._action_repo = action_repo
        self._price_repo = price_repo
        self._projection = projection
        # Verilirse olay DuckDB piyasa geçmişine ONAYLI faktör olarak kaydedilir (yansıtma bu faktörü kullanır)
        self._stock_repo = stock_repo
        self._market_action_service = market_action_service

    def adjust_prices_for_action(self, action_id: int) -> PriceAdjustmentResult:
        action = self._action_repo.get_by_id(action_id)
        if action is None:
            raise ValueError(f"Kurumsal islem bulunamadi: id={action_id}")
        if not action.applied:
            raise ValueError("Fiyat gecmisi duzeltmeden once kurumsal islem portfoye uygulanmalidir.")
        return self.adjust_prices_for_applied_action(action)

    def adjust_prices_for_applied_action(self, action: CorporateAction) -> PriceAdjustmentResult:
        """Faktörü DuckDB piyasa geçmişine onaylı olay olarak kaydeder ve hissenin SQLite yansımasını yeniler.

        SQLite fiyatları doğrudan çarpılmaz: fiyatın sahibi DuckDB'dir, faktör okuma anında uygulanır
        (`PriceProjectionService`). Kaynak geçmişi zaten düzelttiyse (ham seride kırılma yok) olay NO_BREAK
        kaydedilir ve fiyatlar değişmez.
        """
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
        self._register_in_market_history(action, factor)
        adjusted_count = self._project(action.stock_id)
        self._action_repo.mark_prices_adjusted(action.id, factor, adjusted_count)
        return PriceAdjustmentResult(
            action_id=action.id,
            stock_id=action.stock_id,
            factor=factor,
            adjusted_count=adjusted_count,
        )

    def _project(self, stock_id: int) -> int:
        if self._projection is None:
            logger.warning("Fiyat yansıtması yapılandırılmamış; SQLite fiyat geçmişi güncellenmedi (stock_id=%s)", stock_id)
            return 0
        return self._projection.project([stock_id]).written_count

    def _register_in_market_history(self, action: CorporateAction, factor: Decimal) -> None:
        """DuckDB tarafı başarısız olursa yansıtma eski faktörlerle yapılır; hata loglanır."""
        if self._market_action_service is None or self._stock_repo is None:
            return
        try:
            stock = next((s for s in self._stock_repo.get_all_stocks() if s.id == action.stock_id), None)
            if stock is not None:
                self._market_action_service.register_portfolio_action(
                    stock.ticker, replace(action, price_adjustment_factor=factor)
                )
        except Exception as exc:
            logger.warning("Kurumsal aksiyon DuckDB piyasa geçmişine kaydedilemedi: %s", exc)

    def _factor_for_action(self, action: CorporateAction) -> Decimal:
        if action.action_type == ActionType.BEDELSIZ:
            return calculate_price_adjustment_factor(action)

        previous_price_date = action.ex_date - timedelta(days=1)
        previous_daily = self._price_repo.get_last_price_before(action.stock_id, previous_price_date)
        previous_close = previous_daily.close_price if previous_daily else None
        return calculate_price_adjustment_factor(action, previous_close)


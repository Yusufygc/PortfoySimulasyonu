# src/ui/pages/model_portfolio/utils/portfolio_price_updater.py

import logging
from decimal import Decimal
from typing import Dict
from src.ui.shared.price_event_publisher import publish_prices_updated
from src.ui.widgets.shared import Toast

logger = logging.getLogger(__name__)


class PortfolioPriceUpdater:
    def __init__(self, page) -> None:
        self.page = page

    def refresh_prices(self) -> None:
        if self.page.current_portfolio_id is None:
            return
        if not self.page.price_lookup_func:
            Toast.warning(self.page, "Fiyat sorgulama fonksiyonu mevcut değil.")
            return

        positions = self.page.model_portfolio_service.get_positions_with_details(self.page.current_portfolio_id)
        updated_count = 0
        event_prices: Dict[int, Decimal] = {}

        for pos in positions:
            try:
                result = self.page.price_lookup_func(pos["ticker"])
                if result:
                    self.page.current_price_map[pos["stock_id"]] = result.price
                    event_prices[pos["stock_id"]] = result.price
                    updated_count += 1
            except Exception as exc:
                logger.error("Fiyat alınamadı: %s - %s", pos["ticker"], exc)

        publish_prices_updated(getattr(self.page.container, "event_bus", None), event_prices)

        self.page._update_view()

        if updated_count <= 0:
            Toast.warning(
                self.page,
                "Güncellenecek fiyat bulunamadı.",
                duration_ms=self.page.LAST_UPDATE_TOAST_DURATION_MS,
                position="top",
            )
            return

        self.page.record_last_update_time()
        self.page.show_last_update_toast_once(
            force=True,
            detail=f"{updated_count} hisse için fiyat güncellendi.",
        )


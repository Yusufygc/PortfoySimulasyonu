from src.ui.shared.locale_tr import L10N
# src/ui/pages/model_portfolio/utils/portfolio_price_updater.py

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict
from src.domain.models.latest_price import LatestPrice
from src.ui.shared.price_event_publisher import publish_prices_updated
from src.ui.widgets.shared import Toast

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


class PortfolioPriceUpdater:
    def __init__(self, page) -> None:
        self.page = page

    def refresh_prices(self) -> int:
        if self.page.current_portfolio_id is None:
            return 0
        if not self.page.price_lookup_func:
            raise ValueError(L10N.FIYAT_SORGULAMA_FONKSIYONU_MEVCUT_DEGIL)

        positions = self.page.model_portfolio_service.get_positions_with_details(self.page.current_portfolio_id)
        updated_count = 0
        event_prices: Dict[int, Decimal] = {}
        latest_prices = []

        for pos in positions:
            try:
                result = self.page.price_lookup_func(pos["ticker"])
                if result:
                    self.page.current_price_map[pos["stock_id"]] = result.price
                    event_prices[pos["stock_id"]] = result.price
                    latest_prices.append(
                        LatestPrice(
                            id=None,
                            stock_id=pos["stock_id"],
                            price=result.price,
                            as_of=result.as_of,
                            source=result.source,
                            provider="price_lookup",
                            fetched_at=datetime.now(timezone.utc),
                        )
                    )
                    updated_count += 1
            except Exception as exc:
                logger.error("Fiyat alınamadı: %s - %s", pos["ticker"], exc)

        if updated_count > 0:
            latest_price_repo = self.page.__dict__.get("latest_price_repo")
            if latest_price_repo is not None:
                latest_price_repo.upsert_latest_prices(latest_prices)

        return updated_count, event_prices

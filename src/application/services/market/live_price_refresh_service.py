from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Dict, Iterable, List

from src.application.services.market.price_data_health_service import PRICE_SCOPE_ALL_ACTIVE
from src.application.services.market.price_lookup_service import PriceLookupResult, PriceLookupService
from src.domain.models.latest_price import LatestPrice
from src.domain.ports.repositories.i_latest_price_repo import ILatestPriceRepository
from src.domain.ports.repositories.i_stock_repo import IStockRepository

logger = logging.getLogger(__name__)

DEFAULT_TIME_BUDGET_SECONDS = 120.0


@dataclass(frozen=True)
class LivePriceRefreshResult:
    scanned_count: int
    updated_count: int
    prices: Dict[int, Decimal]
    errors: List[str] = field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class LivePriceRefreshService:
    """Refresh latest/intraday prices for active positions without writing daily_prices."""

    # Bir yenileme turunun en uzun süresi; aşılırsa kalan hisseler atlanır (takılı kalmayı önler)
    time_budget_seconds: float = DEFAULT_TIME_BUDGET_SECONDS

    def __init__(
        self,
        stock_repo: IStockRepository,
        price_lookup_service: PriceLookupService,
        price_data_health_service,
        latest_price_repo: ILatestPriceRepository | None = None,
        extra_stock_ids_provider: Callable[[], Iterable[int]] | None = None,
    ) -> None:
        self._stock_repo = stock_repo
        self._price_lookup_service = price_lookup_service
        self._price_data_health_service = price_data_health_service
        self._latest_price_repo = latest_price_repo
        self._extra_stock_ids_provider = extra_stock_ids_provider

    def _target_stock_ids(self, scope: str | None) -> List[int]:
        """Pozisyonlu hisseler ve (varsa) ek kaynaktaki hisseler (ör. izleme listeleri)."""
        stock_ids = set(self._price_data_health_service.active_stock_ids(scope))
        if self._extra_stock_ids_provider is not None:
            try:
                stock_ids.update(self._extra_stock_ids_provider())
            except Exception as exc:
                logger.warning("Ek hisse kaynağı okunamadı: %s", exc)
        return sorted(stock_ids)

    def refresh_active_prices(self, scope: str | None = PRICE_SCOPE_ALL_ACTIVE) -> LivePriceRefreshResult:
        started_at = datetime.now(timezone.utc)
        deadline = time.monotonic() + self.time_budget_seconds
        stock_ids = self._target_stock_ids(scope)
        ticker_map = self._stock_repo.get_ticker_map_for_stock_ids(stock_ids)

        errors: List[str] = [f"{sid}: ticker bulunamadi." for sid in stock_ids if not ticker_map.get(sid)]
        tickers = {sid: ticker_map[sid] for sid in stock_ids if ticker_map.get(sid)}
        results = self._lookup_bulk(tickers)
        results.update(self._lookup_one_by_one({sid: t for sid, t in tickers.items() if sid not in results}, deadline, errors))

        fetched_at = datetime.now(timezone.utc)
        latest_prices = [
            LatestPrice(id=None, stock_id=sid, price=res.price, as_of=res.as_of, source=res.source,
                        provider="price_lookup", fetched_at=fetched_at)
            for sid, res in results.items()
        ]
        if self._latest_price_repo is not None:
            self._latest_price_repo.upsert_latest_prices(latest_prices)

        prices: Dict[int, Decimal] = {sid: res.price for sid, res in results.items()}
        return LivePriceRefreshResult(
            scanned_count=len(stock_ids),
            updated_count=len(prices),
            prices=prices,
            errors=errors,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )

    def _lookup_bulk(self, tickers: Dict[int, str]) -> Dict[int, PriceLookupResult]:
        """Tek toplu istek (hisse başına ~2 sn'lik tekli sorgu yerine); desteklenmiyorsa boş döner."""
        bulk = getattr(self._price_lookup_service, "lookup_prices_bulk", None)
        if bulk is None or not tickers:
            return {}
        try:
            by_ticker = bulk(list(tickers.values())) or {}
        except Exception as exc:
            logger.warning("Toplu canlı fiyat sorgusu başarısız; tekli sorguya geçiliyor: %s", exc)
            return {}
        return {sid: by_ticker[ticker] for sid, ticker in tickers.items() if ticker in by_ticker}

    def _lookup_one_by_one(self, tickers: Dict[int, str], deadline: float, errors: List[str]) -> Dict[int, PriceLookupResult]:
        """Toplu istekte gelmeyen hisseler için tekli sorgu (zaman bütçesi içinde)."""
        results: Dict[int, PriceLookupResult] = {}
        items = list(tickers.items())
        for position, (stock_id, ticker) in enumerate(items):
            if time.monotonic() > deadline:
                errors.append(f"Zaman bütçesi doldu: {len(items) - position} hisse atlandı.")
                logger.warning("Canlı fiyat yenileme zaman bütçesini aştı; %d hisse atlandı.", len(items) - position)
                break
            try:
                result = self._price_lookup_service.lookup_price_for_ticker(ticker)
            except Exception as exc:
                logger.warning("Live price lookup failed for %s: %s", ticker, exc)
                errors.append(f"{ticker}: {exc}")
                continue
            if result is None:
                errors.append(f"{ticker}: fiyat bulunamadi.")
                continue
            results[stock_id] = result
        return results

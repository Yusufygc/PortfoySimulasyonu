"""Haber sorgusu yapılacak takip hedeflerini toplar: BIST portföyü, varlık defteri ve izleme listeleri."""
from __future__ import annotations

import logging
from typing import List

from src.domain.models.asset import AssetClass
from src.domain.models.news_item import NewsTarget, TargetKind

logger = logging.getLogger(__name__)

MAX_TARGETS = 30

_ASSET_KIND = {
    AssetClass.US_STOCK: TargetKind.US_STOCK,
    AssetClass.CRYPTO: TargetKind.CRYPTO,
    AssetClass.PRECIOUS_METAL: TargetKind.METAL,
}


def _clean(ticker: str) -> str:
    return ticker.replace(".IS", "").strip().upper()


class NewsTargetService:
    def __init__(self, portfolio_service, stock_lookup_service, asset_ledger_service, watchlist_service) -> None:
        self._portfolio = portfolio_service
        self._stock_lookup = stock_lookup_service
        self._assets = asset_ledger_service
        self._watchlists = watchlist_service

    def get_targets(self) -> List[NewsTarget]:
        """Portföy hedefleri önce gelir; aynı (tür, sembol) bir kez yer alır; en çok `MAX_TARGETS` hedef."""
        found: List[NewsTarget] = []
        for reader in (self._portfolio_targets, self._asset_targets, self._watchlist_targets):
            try:
                found.extend(reader())
            except Exception as exc:  # bir kaynağın hatası diğer hedefleri engellemez
                logger.warning("Haber hedefleri okunamadı (%s): %s", reader.__name__, exc)
        unique = {(t.kind, t.symbol): t for t in reversed(found)}  # tekrarlarda ilk (portföy) kayıt kalır
        ordered = [t for t in found if unique.get((t.kind, t.symbol)) is t]
        return ordered[:MAX_TARGETS]

    def _portfolio_targets(self) -> List[NewsTarget]:
        active = self._portfolio.get_current_portfolio().active_positions
        stocks = self._stock_lookup.get_stocks(list(active))
        return [
            NewsTarget(_clean(stock.ticker), (stock.name or stock.ticker).strip(), TargetKind.BIST)
            for stock in stocks.values()
        ]

    def _asset_targets(self) -> List[NewsTarget]:
        return [
            NewsTarget(asset.yf_symbol, asset.name, _ASSET_KIND[asset.asset_class])
            for asset in self._assets.list_assets(active_only=True)
        ]

    def _watchlist_targets(self) -> List[NewsTarget]:
        targets: List[NewsTarget] = []
        for watchlist in self._watchlists.get_all_watchlists():
            for entry in self._watchlists.get_watchlist_stocks(watchlist.id):
                if entry.get("stock") is not None:
                    targets.append(NewsTarget(_clean(entry["ticker"]), str(entry["name"]), TargetKind.BIST))
        return targets

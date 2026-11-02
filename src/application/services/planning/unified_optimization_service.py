"""Birleşik portföy (BIST + BIST dışı varlıklar) için optimizasyon girdisi: TL fiyat matrisi ve güncel ağırlıklar.

BIST hisse fiyatları mevcut piyasa verisinden, varlık fiyatları varlık defterinin günlük kapanışlarından gelir ve TL'ye
(gün gün USDTRY ile; altın gram fiyatı dahil) çevrilir. Tarih ekseni BIST işlem günleridir; hafta sonu hareket eden varlıklar
(kripto) bir sonraki BIST gününün getirisine yansır. Nakit optimizasyon kapsamı dışındadır (ağırlıklar yalnızca pozisyonlar arasındadır).
"""
from __future__ import annotations

from datetime import timedelta
from typing import Dict, List, NamedTuple, Optional, Set

import numpy as np
import pandas as pd

from src.domain.market_clock import market_today
from src.domain.models.asset import Asset
from src.domain.models.unified_portfolio import AllocationClass, HoldingValuation

MIN_HOLDINGS = 2
HISTORY_DAYS = 504
MIN_HISTORY_ROWS = 60


class UnifiedUniverse(NamedTuple):
    price_df: pd.DataFrame          # sütun: sembol, değer: TL birim fiyat (ortak tarih ekseni)
    symbols: List[str]              # tüm pozisyonlar (fiyat geçmişi olmayanlar dahil)
    names: Dict[str, str]
    values_try: Dict[str, float]    # güncel TL değer
    last_prices_try: Dict[str, float]
    fractional: Set[str]            # kesirli miktarla işlem gören (BIST dışı) semboller


def asset_try_series(asset: Asset, closes: Dict, fx_rates: Dict) -> pd.Series:
    """Varlığın günlük kapanışını TL birim fiyata çevirir (gram altın: ons/31,1035 x USDTRY). Kur günlere ileri taşınır."""
    if not closes:
        return pd.Series(dtype=float)
    prices = pd.Series({pd.Timestamp(day): float(asset.unit_price(value)) for day, value in closes.items()}).sort_index()
    if asset.quote_currency == "TRY":
        return prices
    if not fx_rates:
        return pd.Series(dtype=float)
    rates = pd.Series({pd.Timestamp(day): float(value) for day, value in fx_rates.items()}).sort_index()
    aligned = rates.reindex(rates.index.union(prices.index)).ffill().reindex(prices.index)
    return (prices * aligned).dropna()


def combine_prices(bist_df: pd.DataFrame, asset_series: Dict[str, pd.Series]) -> pd.DataFrame:
    """BIST günlerine hizalı tek fiyat matrisi; BIST yoksa varlık günlerinin birleşimi. Eksikler ileri taşınır."""
    assets_df = pd.DataFrame({symbol: series for symbol, series in asset_series.items() if not series.empty}).sort_index()
    if bist_df is not None and not bist_df.empty:
        base = bist_df.copy()
        base.index = pd.to_datetime(base.index)
        if assets_df.empty:
            return base
        assets_df = assets_df.reindex(assets_df.index.union(base.index)).ffill().reindex(base.index)
        return pd.concat([base, assets_df], axis=1)
    return assets_df.ffill()


def trim_to_common_history(frame: pd.DataFrame, min_rows: int = MIN_HISTORY_ROWS) -> pd.DataFrame:
    """Ortak geçmiş `min_rows` günden kısaysa en kısa geçmişli sütunu çıkarır (güncel ağırlığında kalır); sonra eksik satırları atar."""
    frame = frame.replace([np.inf, -np.inf], np.nan)
    while frame.shape[1] > 1:
        common = frame.dropna(how="any")
        if len(common) >= min_rows:
            return common
        counts = frame.notna().sum()
        frame = frame.drop(columns=[counts.idxmin()])
    return frame.dropna(how="any")


class UnifiedOptimizationService:
    def __init__(self, unified_portfolio, optimization_service, asset_repo, asset_price_repo, fx_rate_repo) -> None:
        self._unified = unified_portfolio
        self._optimizer = optimization_service
        self._asset_repo = asset_repo
        self._asset_price_repo = asset_price_repo
        self._fx_rate_repo = fx_rate_repo

    def _holdings(self) -> List[HoldingValuation]:
        holdings = [h for h in self._unified.get_summary("TRY").holdings if h.quantity > 0 and h.value_try > 0]
        if len(holdings) < MIN_HOLDINGS:
            raise ValueError("Optimizasyon için portföyde en az 2 farklı varlık olmalıdır.")
        return holdings

    def _asset_series(self, holdings: List[HoldingValuation]) -> Dict[str, pd.Series]:
        end = market_today()
        start = end - timedelta(days=HISTORY_DAYS * 2)   # ~504 işlem günü için takvim günü payı
        series: Dict[str, pd.Series] = {}
        fx_cache: Dict[str, Dict] = {}
        for holding in holdings:
            asset = self._asset_repo.get_asset(holding.ref_id) if holding.allocation_class != AllocationClass.BIST_STOCK else None
            if asset is None:
                continue
            closes = {p.price_date: p.close_price for p in self._asset_price_repo.get_daily_prices(asset.id, start, end)}
            if asset.quote_currency != "TRY" and asset.quote_currency not in fx_cache:
                fx_cache[asset.quote_currency] = {
                    r.rate_date: r.rate for r in self._fx_rate_repo.get_rates(asset.quote_currency, "TRY", start, end)
                }
            series[holding.symbol] = asset_try_series(asset, closes, fx_cache.get(asset.quote_currency, {}))
        return series

    def load_universe(self) -> UnifiedUniverse:
        holdings = self._holdings()
        bist = [h.symbol for h in holdings if h.allocation_class == AllocationClass.BIST_STOCK]
        bist_df = self._optimizer._get_historical_prices(bist, HISTORY_DAYS) if bist else pd.DataFrame()
        frame = trim_to_common_history(combine_prices(bist_df, self._asset_series(holdings)))
        return UnifiedUniverse(
            price_df=frame,
            symbols=[h.symbol for h in holdings],
            names={h.symbol: h.name for h in holdings},
            values_try={h.symbol: float(h.value_try) for h in holdings},
            last_prices_try={h.symbol: float(h.value_try / h.quantity) for h in holdings},
            fractional={h.symbol for h in holdings if h.allocation_class != AllocationClass.BIST_STOCK},
        )

    def optimize(self, universe: UnifiedUniverse, policy=None):
        total = sum(universe.values_try.values())
        weights = np.array([universe.values_try[symbol] / total for symbol in universe.symbols])
        return self._optimizer._optimize(universe.symbols, weights, policy=policy, price_df=universe.price_df)

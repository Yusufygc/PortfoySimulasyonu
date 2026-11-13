"""Genel Bakış grafiği için varlık defteri fiyat serileri (BIST dışı semboller)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

from src.domain.market_clock import market_today
from src.domain.models.asset import Asset

DEFAULT_HISTORY_YEARS = 3


@dataclass(frozen=True)
class AssetChartSeries:
    symbol: str
    name: str
    currency: str
    points: Tuple[Tuple[date, Decimal], ...]  # tarihe göre artan günlük kapanışlar (varlığın kendi para biriminde)


class AssetChartService:
    """Varlık sembolünü (`BTC` veya `BTC-USD`) defterdeki varlığa eşler ve kayıtlı günlük kapanışlarını döner.

    Yalnızca yerel veritabanını okur (ağ yok); geçmiş varlık eklenirken ve fiyat yenilemede doldurulur.
    """

    def __init__(self, asset_ledger_service, asset_price_repo) -> None:
        self._assets = asset_ledger_service
        self._prices = asset_price_repo

    def find_asset(self, symbol: str) -> Optional[Asset]:
        wanted = (symbol or "").strip().upper()
        if not wanted:
            return None
        for asset in self._assets.list_assets(active_only=True):
            if wanted in (asset.symbol.upper(), asset.yf_symbol.upper()):
                return asset
        return None

    def list_chart_symbols(self) -> List[Tuple[str, str]]:
        """Grafik hızlı seçicisi için `(sembol, etiket)` çiftleri; sembol grafiğe verilen yfinance sembolüdür."""
        return [(asset.yf_symbol, asset.symbol) for asset in self._assets.list_assets(active_only=True)]

    def get_series(self, symbol: str, years: int = DEFAULT_HISTORY_YEARS) -> Optional[AssetChartSeries]:
        asset = self.find_asset(symbol)
        if asset is None or asset.id is None:
            return None
        end = market_today()
        rows = self._prices.get_daily_prices(asset.id, end - timedelta(days=365 * years), end)
        points = tuple((row.price_date, row.close_price) for row in sorted(rows, key=lambda r: r.price_date))
        return AssetChartSeries(asset.symbol, asset.name, asset.quote_currency, points)

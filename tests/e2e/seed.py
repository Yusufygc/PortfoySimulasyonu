"""Test veritabanı tohumlama yardımcıları: ağ gerektiren dış kaynakların (kur, varlık fiyatı, sembol doğrulama) yerine
port düzeyinde deterministik karşılıklar koyar. Uygulama kodu değişmez; yalnızca dış bağımlılık taklit edilir."""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional


class FakeSymbolVerifier:
    """`IAssetSymbolVerifier` taklidi: bilinen semboller doğrulanır, para birimi sabittir."""

    def __init__(self, known: dict[str, str]) -> None:
        self.known = known

    def verify(self, yf_symbol: str) -> bool:
        return yf_symbol in self.known

    def currency_of(self, yf_symbol: str) -> Optional[str]:
        return self.known.get(yf_symbol)


def seed_fx(container, days: int = 130, start: str = "34.0") -> Decimal:
    """Deterministik USD/TRY kur serisi yazar; son kuru döndürür."""
    from src.domain.models.asset_price import FxRate

    rnd = random.Random(7)
    today = date.today()
    rate, rates = Decimal(start), []
    for i in range(days, -1, -1):
        rate = (rate * Decimal(str(1 + rnd.uniform(-0.002, 0.004)))).quantize(Decimal("0.0001"))
        rates.append(FxRate(None, "USD", "TRY", today - timedelta(days=i), rate, "e2e"))
    container.fx_rate_repo.upsert_rates(rates)
    return rate


def seed_asset_prices(container, asset, start_price: float, days: int = 130, seed: int = 1):
    """Varlık günlük kapanış serisi ve son fiyat (varlığın kendi fiyat biriminde)."""
    from src.domain.models.asset_price import AssetLatestPrice, AssetPrice

    rnd = random.Random(seed)
    today = date.today()
    price, rows = Decimal(str(start_price)), []
    for i in range(days, -1, -1):
        price = max(Decimal("0.01"), (price * Decimal(str(1 + rnd.uniform(-0.02, 0.024)))).quantize(Decimal("0.0001")))
        rows.append(AssetPrice(None, asset.id, today - timedelta(days=i), price, asset.quote_currency, "e2e"))
    container.asset_price_repo.upsert_daily_prices(rows)
    now = datetime.now()
    container.asset_price_repo.upsert_latest_prices(
        [AssetLatestPrice(None, asset.id, rows[-1].close_price, asset.quote_currency, now, "e2e", now)])
    return rows

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Iterable, Optional

from src.domain.market_clock import market_today
from src.domain.models.asset_price import FxRate
from src.domain.ports.repositories.i_fx_rate_repo import IFxRateRepository
from src.domain.ports.services.i_asset_price_provider import IAssetPriceProvider

SOURCE = "yfinance"
DEFAULT_BACKFILL_DAYS = 365


def fx_symbol(base_currency: str, quote_currency: str) -> str:
    """yfinance kur sembolü: USD tabanlı çiftler `TRY=X`, diğerleri `EURTRY=X` biçimindedir."""
    base, quote = base_currency.upper(), quote_currency.upper()
    return f"{quote}=X" if base == "USD" else f"{base}{quote}=X"


class FxRateService:
    """Kur okuma ve yenileme: işlem anı ve güncel kurlar `fx_rates` tablosundan okunur."""

    def __init__(self, provider: IAssetPriceProvider, repo: IFxRateRepository) -> None:
        self._provider = provider
        self._repo = repo

    def get_rate(self, base_currency: str, quote_currency: str, on_date: Optional[date] = None) -> Optional[Decimal]:
        """`on_date` (yoksa en güncel) için 1 `base` kaç `quote`; bilinmiyorsa None. Aynı para biriminde 1."""
        base, quote = base_currency.upper(), quote_currency.upper()
        if base == quote:
            return Decimal("1")
        cutoff = on_date or date.max
        direct = self._repo.get_rate_on_or_before(base, quote, cutoff)
        if direct is not None:
            return direct.rate
        inverse = self._repo.get_rate_on_or_before(quote, base, cutoff)
        return Decimal("1") / inverse.rate if inverse is not None else None

    def convert(
        self, amount: Decimal, from_currency: str, to_currency: str, on_date: Optional[date] = None
    ) -> Optional[Decimal]:
        rate = self.get_rate(from_currency, to_currency, on_date)
        return amount * rate if rate is not None else None

    def refresh_latest(self, currencies: Iterable[str], quote_currency: str = "TRY") -> Dict[str, Decimal]:
        """Her para birimi için güncel kuru çekip kaydeder; alınan kurları döner (alınamayanlar yer almaz)."""
        quote = quote_currency.upper()
        wanted = {c.upper() for c in currencies if c and c.upper() != quote}
        symbol_by_currency = {currency: fx_symbol(currency, quote) for currency in sorted(wanted)}
        quotes = self._provider.get_latest(list(symbol_by_currency.values()))
        rates: Dict[str, Decimal] = {}
        records = []
        for currency, symbol in symbol_by_currency.items():
            quote_item = quotes.get(symbol)
            if quote_item is None:
                continue
            rates[currency] = quote_item.price
            records.append(FxRate(None, currency, quote, quote_item.as_of.date(), quote_item.price, SOURCE))
        self._repo.upsert_rates(records)
        return rates

    def backfill(
        self, base_currency: str, quote_currency: str = "TRY", start: Optional[date] = None, end: Optional[date] = None
    ) -> int:
        """Geçmiş günlük kurları çekip kaydeder; kaydedilen gün sayısını döner."""
        end_date = end or market_today()
        start_date = start or end_date - timedelta(days=DEFAULT_BACKFILL_DAYS)
        symbol = fx_symbol(base_currency, quote_currency)
        points = self._provider.get_history(symbol, start_date, end_date)
        self._repo.upsert_rates(
            FxRate(None, base_currency, quote_currency, point_date, close, SOURCE) for point_date, close in points
        )
        return len(points)

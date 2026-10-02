"""Üst piyasa şeridi: USD/TRY, EUR/TRY, BIST 100, gram altın ve gram gümüş (TRY)."""
from __future__ import annotations

import logging
from typing import List, Optional

from src.domain.models.market_indicator import IndicatorQuote, MarketIndicator
from src.domain.ports.services.i_market_indicator_provider import IMarketIndicatorProvider

logger = logging.getLogger(__name__)

TROY_OZ_TO_GRAM = 31.1035

# (etiket, sembol, para birimi) — USD/TRY altın/gümüş TRY dönüşümü için önce okunur
_SIMPLE = (
    ("USD/TRY", "TRY=X", "₺"),
    ("EUR/TRY", "EURTRY=X", "₺"),
    ("BIST 100", "XU100.IS", ""),
)
_METALS = (  # USD/troy ons -> TRY/gram
    ("ALTIN", "GC=F", "₺"),
    ("GÜMÜŞ", "SI=F", "₺"),
)
DISPLAY_ORDER = ("ALTIN", "GÜMÜŞ", "USD/TRY", "EUR/TRY", "BIST 100")


def _change_pct(quote: IndicatorQuote) -> Optional[float]:
    if quote.previous_close and quote.previous_close > 0:
        return (quote.last - quote.previous_close) / quote.previous_close * 100.0
    return None


class MarketIndicatorsService:
    def __init__(self, provider: IMarketIndicatorProvider) -> None:
        self._provider = provider

    def get_indicators(self) -> List[MarketIndicator]:
        """Alınabilen göstergeler `DISPLAY_ORDER` sırasıyla; alınamayanlar atlanır."""
        found: dict[str, MarketIndicator] = {}
        usd_try: Optional[float] = None

        for label, symbol, currency in _SIMPLE:
            quote = self._provider.get_quote(symbol)
            if quote is None:
                continue
            found[label] = MarketIndicator(label, quote.last, currency, _change_pct(quote))
            if label == "USD/TRY":
                usd_try = quote.last

        for label, symbol, currency in _METALS:
            quote = self._provider.get_quote(symbol)
            if quote is None:
                continue
            # USD/TRY alınamadıysa USD/gram gösterilir (para birimi boş bırakılır)
            rate = usd_try if usd_try is not None else 1.0
            found[label] = MarketIndicator(
                label,
                quote.last * rate / TROY_OZ_TO_GRAM,
                currency if usd_try is not None else "$",
                _change_pct(quote),
            )
        return [found[label] for label in DISPLAY_ORDER if label in found]

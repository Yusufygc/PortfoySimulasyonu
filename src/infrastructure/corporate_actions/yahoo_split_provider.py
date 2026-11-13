"""Yahoo Finance bölünme kayıtları (`Ticker.splits`) -> bölünme sinyali."""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Callable, List, Sequence

import yfinance as yf

from src.domain.models.split_signal import SplitSignal, SplitSource
from src.domain.ports.services.i_split_signal_provider import ISplitSignalProvider, SplitTarget
from src.infrastructure.market_data._errors import MARKET_DATA_FALLBACK_ERRORS
from src.infrastructure.retry import retry_call

logger = logging.getLogger(__name__)

SplitsFetcher = Callable[[str], "object"]  # yf sembolü -> pandas Series (index: zaman, değer: oran)


def _fetch_splits(yf_symbol: str):
    from src.infrastructure.market_data.yfinance_lock import yfinance_lock

    def fetch():
        with yfinance_lock:
            return yf.Ticker(yf_symbol).splits

    return retry_call(fetch, label=f"{yf_symbol} bölünme kaydı")


class YahooSplitProvider(ISplitSignalProvider):
    def __init__(self, fetcher: SplitsFetcher | None = None) -> None:
        self._fetcher = fetcher or _fetch_splits

    def fetch_signals(self, targets: Sequence[SplitTarget], since: date) -> List[SplitSignal]:
        signals: List[SplitSignal] = []
        for target in targets:
            try:
                series = self._fetcher(target.yf_symbol)
            except MARKET_DATA_FALLBACK_ERRORS as exc:
                logger.warning("Yahoo bölünme kaydı okunamadı (%s): %s", target.yf_symbol, exc)
                continue
            signals.extend(self._signals_from_series(target, series, since))
        return signals

    @staticmethod
    def _signals_from_series(target: SplitTarget, series, since: date) -> List[SplitSignal]:
        if series is None or getattr(series, "empty", True):
            return []
        result: List[SplitSignal] = []
        for stamp, value in series.items():
            point_date = stamp.date() if hasattr(stamp, "date") else stamp
            try:
                multiplier = Decimal(str(round(float(value), 6)))  # float kalıntısı: 5.721393000000001
            except (TypeError, ValueError):
                continue
            if point_date < since or multiplier <= 0 or multiplier == 1:
                continue
            result.append(SplitSignal(target.key, point_date, multiplier, SplitSource.YAHOO,
                                      detail=f"Yahoo splits {target.yf_symbol}: {multiplier}"))
        return result

"""Uygulama verisinden ve mevcut kurumsal aksiyon sağlayıcısından bölünme sinyalleri.

- `KapSplitSignalSource`: KAP/MKK bedelsiz adaylarını sinyale çevirir (çarpan = 1 + oran).
- `PriceBreakSplitSignalSource`: (a) DuckDB ham serisindeki kalıcı kırılmalar, (b) SQLite kapanışı ile DuckDB
  düzeltilmiş kapanışı arasındaki kalıcı basamak (Yahoo geçmişi sonradan düzelttiğinde SQLite eski ham fiyatı
  tutar; SDTTR 2026 vakası), (c) DuckDB'de olmayan hissede SQLite serisinin kendi kırılması.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Sequence

from src.domain.market_clock import market_today
from src.domain.models.corporate_action import ActionType
from src.domain.models.split_signal import SplitSignal, SplitSource
from src.domain.ports.repositories.i_market_history_repo import IMarketHistoryRepository
from src.domain.ports.repositories.i_price_repo import IPriceRepository
from src.domain.ports.services.i_corporate_action_provider import (
    CorporateActionProviderUnavailable,
    ICorporateActionProvider,
)
from src.domain.ports.services.i_split_signal_provider import ISplitSignalProvider, SplitTarget
from src.domain.split_detection import persistent_breaks, persistent_steps

logger = logging.getLogger(__name__)

_MULTIPLIER_PLACES = Decimal("0.0001")


def _signal(key: str, point_date: date, multiplier: float, detail: str) -> SplitSignal | None:
    value = Decimal(str(multiplier)).quantize(_MULTIPLIER_PLACES)
    if value <= 0 or value == 1:
        return None
    return SplitSignal(key, point_date, value, SplitSource.PRICE_BREAK, detail=detail)


def _found(key: str, points, detail: str) -> List[SplitSignal]:
    signals = (_signal(key, point_date, mult, detail) for point_date, mult in points)
    return [s for s in signals if s is not None]


def _stored_signals(key: str, stored: dict, adjusted: dict) -> List[SplitSignal]:
    """SQLite serisi: DuckDB varsa düzeltilmiş geçmişe göre basamak, yoksa serinin kendi kırılması."""
    if not adjusted:
        return _found(key, persistent_breaks(list(stored.items())), "SQLite seride kalıcı kırılma")
    ratios = [(d, stored[d] / adjusted[d]) for d in sorted(stored) if adjusted.get(d, 0) > 0]
    return _found(key, persistent_steps(ratios), "SQLite ile düzeltilmiş geçmiş arasında basamak")


def _is_usable_kap(candidate, keys: set, since: date) -> bool:
    if candidate.action_type != ActionType.BEDELSIZ or candidate.ratio is None or candidate.ex_date is None:
        return False
    return candidate.ex_date >= since and candidate.ticker.upper() in keys


def _kap_signal(candidate) -> SplitSignal:
    return SplitSignal(candidate.ticker, candidate.ex_date, Decimal("1") + candidate.ratio, SplitSource.KAP,
                       detail=candidate.source_url or candidate.source_disclosure_id)


class KapSplitSignalSource(ISplitSignalProvider):
    def __init__(self, provider: ICorporateActionProvider) -> None:
        self._provider = provider

    def fetch_signals(self, targets: Sequence[SplitTarget], since: date) -> List[SplitSignal]:
        bist = [t for t in targets if t.stock_id is not None]
        if not bist:
            return []
        keys = {t.key.upper() for t in bist}
        try:
            candidates = self._provider.fetch_candidates([t.key for t in bist], since, None)
        except CorporateActionProviderUnavailable as exc:
            logger.warning("KAP bölünme sinyali okunamadı: %s", exc)
            return []
        return [_kap_signal(c) for c in candidates if _is_usable_kap(c, keys, since)]


class PriceBreakSplitSignalSource(ISplitSignalProvider):
    def __init__(self, history_repo: IMarketHistoryRepository, price_repo: IPriceRepository) -> None:
        self._history = history_repo
        self._prices = price_repo

    def fetch_signals(self, targets: Sequence[SplitTarget], since: date) -> List[SplitSignal]:
        signals: List[SplitSignal] = []
        end = market_today()
        for target in targets:
            if target.stock_id is None:
                continue  # yalnızca BIST hisselerinin fiyat geçmişi uygulamada tutulur
            try:
                signals.extend(self._signals_for(target, since, end))
            except Exception as exc:  # tek hissenin okuma hatası taramayı durdurmaz
                logger.warning("Fiyat kırılması taranamadı (%s): %s", target.key, exc, exc_info=True)
        return signals

    def _signals_for(self, target: SplitTarget, since: date, end: date) -> List[SplitSignal]:
        start = since - timedelta(days=15)  # basamağın öncesini görebilmek için
        raw = {b.price_date: b.close_price for b in self._history.get_price_series(target.key, start, end, adjusted=False)}
        adjusted = {b.price_date: b.close_price for b in self._history.get_price_series(target.key, start, end)}
        stored = {p.price_date: float(p.close_price) for p in self._prices.get_price_series(target.stock_id, start, end)}
        found = _found(target.key, persistent_breaks(list(raw.items())), "DuckDB ham seride kalıcı kırılma")
        found += _stored_signals(target.key, stored, adjusted)
        return [s for s in found if s.ex_date >= since]


class CompositeSplitSignalSource(ISplitSignalProvider):
    """Kaynakları sırayla çalıştırır; bir kaynağın hatası diğerlerini durdurmaz."""

    def __init__(self, sources: Sequence[ISplitSignalProvider]) -> None:
        self._sources = list(sources)

    def fetch_signals(self, targets: Sequence[SplitTarget], since: date) -> List[SplitSignal]:
        signals: List[SplitSignal] = []
        for source in self._sources:
            try:
                signals.extend(source.fetch_signals(targets, since))
            except Exception as exc:
                logger.warning("Bölünme sinyal kaynağı başarısız (%s): %s", type(source).__name__, exc, exc_info=True)
        return signals


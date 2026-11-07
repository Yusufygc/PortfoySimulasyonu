"""Bölünme sinyallerinin kaynaklar arası uzlaşısı (saf fonksiyonlar).

Aynı hisse için ex-date'i en fazla `DATE_WINDOW_DAYS` gün, çarpanı en fazla `MULTIPLIER_TOLERANCE` oranında
ayrışan sinyaller tek olay sayılır. En az iki farklı kaynak (Yahoo, KAP, fiyat kırılması) aynı olayı
gösterirse karar `AUTO`; tek kaynak veya ters bölünme `CANDIDATE`; uygulanmış bir olayla eşleşen grup
`ALREADY_APPLIED` olur.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, Iterable, List, Sequence, Tuple

from src.domain.models.split_signal import (
    MULTIPLIER_PRIORITY,
    SOURCE_PRIORITY,
    SplitDecision,
    SplitDecisionKind,
    SplitSignal,
)

DATE_WINDOW_DAYS = 7  # takvim günü; Yahoo tarihi gerçek ex-date'ten bir hafta sapabilir
MULTIPLIER_TOLERANCE = Decimal("0.02")
MIN_AUTO_SOURCES = 2

AppliedSplit = Tuple[str, date, Decimal]  # (ticker, ex_date, multiplier)


def same_event(a_date: date, a_mult: Decimal, b_date: date, b_mult: Decimal) -> bool:
    if abs((a_date - b_date).days) > DATE_WINDOW_DAYS:
        return False
    return abs(a_mult / b_mult - Decimal("1")) <= MULTIPLIER_TOLERANCE


def _cluster(signals: Sequence[SplitSignal]) -> List[List[SplitSignal]]:
    clusters: List[List[SplitSignal]] = []
    for signal in sorted(signals, key=lambda s: s.ex_date):
        target = next(
            (c for c in clusters if same_event(c[0].ex_date, c[0].multiplier, signal.ex_date, signal.multiplier)),
            None,
        )
        if target is None:
            clusters.append([signal])
        else:
            target.append(signal)
    return clusters


def _representative(cluster: Sequence[SplitSignal]) -> Tuple[date, Decimal]:
    """Ex-date tarih önceliğine, çarpan kesin oran veren en öncelikli kaynağa göre seçilir."""
    dated = min(cluster, key=lambda s: SOURCE_PRIORITY.index(s.source))
    exact = min(cluster, key=lambda s: MULTIPLIER_PRIORITY.index(s.source))
    return dated.ex_date, exact.multiplier


def _decide(cluster: Sequence[SplitSignal], applied: Sequence[AppliedSplit]) -> SplitDecision:
    ticker = cluster[0].ticker
    ex_date, multiplier = _representative(cluster)
    if any(t == ticker and same_event(d, m, ex_date, multiplier) for t, d, m in applied):
        kind = SplitDecisionKind.ALREADY_APPLIED
    elif multiplier > 1 and len({s.source for s in cluster}) >= MIN_AUTO_SOURCES:
        kind = SplitDecisionKind.AUTO
    else:
        kind = SplitDecisionKind.CANDIDATE
    return SplitDecision(ticker, ex_date, multiplier, kind, tuple(cluster))


def match_signals(signals: Iterable[SplitSignal], applied: Iterable[AppliedSplit] = ()) -> List[SplitDecision]:
    """Sinyalleri hisse ve olay bazında gruplar; her olay için bir karar döner (ticker, ex-date sıralı)."""
    applied_list = [(t.strip().upper().replace(".IS", ""), d, Decimal(str(m))) for t, d, m in applied]
    by_ticker: Dict[str, List[SplitSignal]] = {}
    for signal in signals:
        by_ticker.setdefault(signal.ticker, []).append(signal)
    decisions = [
        _decide(cluster, applied_list)
        for ticker in sorted(by_ticker)
        for cluster in _cluster(by_ticker[ticker])
    ]
    return sorted(decisions, key=lambda d: (d.ticker, d.ex_date))

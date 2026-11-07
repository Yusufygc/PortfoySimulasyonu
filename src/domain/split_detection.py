"""Fiyat serilerinde bölünme izleri (saf fonksiyonlar).

İki iz aranır:
- `persistent_steps`: iki kaynağın aynı günlerdeki kapanış oranında kalıcı basamak. SQLite eski ham kapanışı
  tutarken Yahoo/DuckDB geçmişi bölünmeye göre düzelttiyse oran bölünme öncesi çarpana, sonrası 1'e oturur.
- `persistent_breaks`: tek seride kalıcı kırılma (önceki ve sonraki barlar yeni/eski seviyede kalır).
Temettü düzeltmesi ve tek barlık veri hataları eşiklerle elenir.
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional, Sequence, Tuple

MIN_STEP = 1.2          # %20'den küçük basamak bölünme değildir (temettü/veri gürültüsü)
STEP_TOLERANCE = 0.05   # basamağın iki yanı kendi içinde bu oranda tutarlı olmalı
BREAK_DROP = 1.6        # BIST günlük limiti %10; tek günde 1,6 kat düşüş piyasa hareketi değildir
BREAK_RISE = 1.8        # ters bölünme izi
LEVEL_TOLERANCE = 0.12  # kırılma sonrası/öncesi barların seviyede kalma toleransı
WINDOW = 3

Point = Tuple[date, float]


def _median3(values: Sequence[float]) -> float:
    return sorted(values)[len(values) // 2]


def _consistent(values: Sequence[float], level: float, tolerance: float) -> bool:
    return all(abs(v / level - 1.0) <= tolerance for v in values)


def _positive_sorted(points: Sequence[Point]) -> List[Point]:
    return sorted((d, v) for d, v in points if v and v > 0)


def _step_at(points: Sequence[Point], i: int) -> Optional[float]:
    """`i`. noktada iki yanı kendi içinde tutarlı, en az %20'lik bir basamak varsa çarpanı."""
    before = [r for _, r in points[i - WINDOW:i]]
    after = [r for _, r in points[i:i + WINDOW]]
    level_before, level_after = _median3(before), _median3(after)
    multiplier = level_before / level_after
    if not (multiplier >= MIN_STEP or multiplier <= 1.0 / MIN_STEP):
        return None
    if _consistent(before, level_before, STEP_TOLERANCE) and _consistent(after, level_after, STEP_TOLERANCE):
        return multiplier
    return None


def persistent_steps(ratios: Sequence[Point]) -> List[Point]:
    """`(tarih, a/b oranı)` dizisinde kalıcı basamaklar: `(yeni bazdaki ilk gün, önceki oran / sonraki oran)`."""
    points = _positive_sorted(ratios)
    steps: List[Point] = []
    i = WINDOW
    while i <= len(points) - WINDOW:
        multiplier = _step_at(points, i)
        if multiplier is None:
            i += 1
            continue
        steps.append((points[i][0], multiplier))
        i += WINDOW
    return steps


def _break_at(points: Sequence[Point], i: int) -> Optional[float]:
    """`i`. barda kalıcı kırılma varsa çarpan (önceki/yeni kapanış); limit hareketi veya veri hatasında None."""
    prev_close, close = points[i - 1][1], points[i][1]
    multiplier = prev_close / close
    if not (multiplier >= BREAK_DROP or multiplier <= 1.0 / BREAK_RISE):
        return None
    after = [c for _, c in points[i + 1:i + 1 + WINDOW]]
    before = [c for _, c in points[max(0, i - WINDOW):i - 1]]
    if len(after) < WINDOW:
        return None  # kalıcılık henüz görülemiyor
    holds = _consistent(after, close, LEVEL_TOLERANCE) and _consistent(before, prev_close, LEVEL_TOLERANCE)
    return multiplier if holds else None


def persistent_breaks(closes: Sequence[Point]) -> List[Point]:
    """Tek kapanış serisinde kalıcı kırılmalar: `(kırılma sonrası ilk gün, önceki kapanış / yeni kapanış)`."""
    points = _positive_sorted(closes)
    found = ((points[i][0], _break_at(points, i)) for i in range(1, len(points)))
    return [(d, m) for d, m in found if m is not None]

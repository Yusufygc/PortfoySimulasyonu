"""Fiyat serilerinde bölünme izleri (saf fonksiyonlar).

İki iz aranır:
- `persistent_steps`: iki kaynağın aynı günlerdeki kapanış oranında kalıcı basamak. SQLite eski ham kapanışı
  tutarken Yahoo/DuckDB geçmişi bölünmeye göre düzelttiyse oran bölünme öncesi çarpana, sonrası 1'e oturur.
- `persistent_breaks`: tek seride kalıcı kırılma (önceki ve sonraki barlar yeni/eski seviyede kalır).
Temettü düzeltmesi ve tek barlık veri hataları eşiklerle elenir.
"""
from __future__ import annotations

from datetime import date
from typing import List, Sequence, Tuple

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


def persistent_steps(ratios: Sequence[Point]) -> List[Point]:
    """`(tarih, a/b oranı)` dizisinde kalıcı basamaklar: `(yeni bazdaki ilk gün, önceki oran / sonraki oran)`."""
    points = sorted((d, r) for d, r in ratios if r and r > 0)
    steps: List[Point] = []
    i = WINDOW
    while i <= len(points) - WINDOW:
        before = [r for _, r in points[i - WINDOW:i]]
        after = [r for _, r in points[i:i + WINDOW]]
        level_before, level_after = _median3(before), _median3(after)
        multiplier = level_before / level_after
        if (multiplier >= MIN_STEP or multiplier <= 1.0 / MIN_STEP) and _consistent(
            before, level_before, STEP_TOLERANCE
        ) and _consistent(after, level_after, STEP_TOLERANCE):
            steps.append((points[i][0], multiplier))
            i += WINDOW
            continue
        i += 1
    return steps


def persistent_breaks(closes: Sequence[Point]) -> List[Point]:
    """Tek kapanış serisinde kalıcı kırılmalar: `(kırılma sonrası ilk gün, önceki kapanış / yeni kapanış)`."""
    points = sorted((d, c) for d, c in closes if c and c > 0)
    breaks: List[Point] = []
    for i in range(1, len(points)):
        prev_close, close = points[i - 1][1], points[i][1]
        multiplier = prev_close / close
        if not (multiplier >= BREAK_DROP or multiplier <= 1.0 / BREAK_RISE):
            continue
        after = [c for _, c in points[i + 1:i + 1 + WINDOW]]
        before = [c for _, c in points[max(0, i - WINDOW):i - 1]]
        if len(after) < WINDOW:
            continue  # kalıcılık henüz görülemiyor
        if _consistent(after, close, LEVEL_TOLERANCE) and _consistent(before, prev_close, LEVEL_TOLERANCE):
            breaks.append((points[i][0], multiplier))
    return breaks
